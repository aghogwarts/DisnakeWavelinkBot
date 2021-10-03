"""The MIT License (MIT)
Copyright (c) 2019-2020 PythonistaGuild
Permission is hereby granted, free of charge, to any person obtaining a
copy of this software and associated documentation files (the "Software"),
to deal in the Software without restriction, including without limitation
the rights to use, copy, modify, merge, publish, distribute, sublicense,
and/or sell copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following conditions:
The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
DEALINGS IN THE SOFTWARE.
-------------------------------------------------------------------------------
This example is taken from wavelink repo and its modified and uses the following which must be installed prior to running:
    - disnake.py version >= 2.1.2 (pip install -U disnake.py)
    - Wavelink version >= 0.5.1 (pip install -U wavelink)

--------------------------------------------------------------------------------
"""
from youtubesearchpython.__future__ import ChannelsSearch, VideosSearch
import asyncio
import time
import async_timeout
import copy
import datetime
import disnake
import math
import random
import re
import typing
import youtube_dl as ydl
import humanize

from MusicBot import Bot
from jishaku.functools import executor_function
import wavelink
from disnake.ext import commands

from bot_utils.menus import button, Menu, ListPageSource, MenuPages

# URL matching REGEX...
from bot_utils.paginator import Paginator

URL_REG = re.compile(r'https?://(?:www\.)?.+')


@executor_function
def youtube(query, download=False):
    ytdl = ydl.YoutubeDL(
        {"format": "bestaudio/best", "restrictfilenames": True, "noplaylist": True, "nocheckcertificate": True,
         "ignoreerrors": True, "logtostderr": False, "quiet": True, "no_warnings": True, "default_search": "auto",
         "source_address": "0.0.0.0"})
    info = ytdl.extract_info(query, download=download)
    del ytdl
    return info


class NoChannelProvided(commands.CommandError):
    """Error raised when no suitable voice channel was supplied."""
    pass


class IncorrectChannelError(commands.CommandError):
    """Error raised when commands are issued outside of the players session channel."""
    pass


class Track(wavelink.Track):
    """Wavelink Track object with a requester attribute."""

    __slots__ = ('requester',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args)

        self.requester = kwargs.get('requester')


class Player(wavelink.Player):
    """Custom wavelink Player class."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.context: commands.Context = kwargs.get('context', None)
        if self.context:
            self.dj: disnake.Member = self.context.author

        self.queue = asyncio.Queue()
        self.controller = None
        self._loop = False

        self.waiting = False
        self.updating = False
        self.now = None

        self.pause_votes = set()
        self.resume_votes = set()
        self.skip_votes = set()
        self.shuffle_votes = set()
        self.stop_votes = set()

    async def do_next(self) -> None:
        if self.is_playing or self.waiting:
            return

        # Clear the votes for a new song...
        self.pause_votes.clear()
        self.resume_votes.clear()
        self.skip_votes.clear()
        self.shuffle_votes.clear()
        self.stop_votes.clear()

        if not self.loop:

            try:
                self.waiting = True
                with async_timeout.timeout(300):
                    track = await self.queue.get()
            except asyncio.TimeoutError:
                # No music has been played for 5 minutes, cleanup and disconnect...
                return await self.teardown()
        if self.loop is True:
            track = await self.last_position
            await self.play(track)

        await self.play(track)
        self.waiting = False

        # Invoke our players controller...
        await self.invoke_controller()

    async def invoke_controller(self) -> None:
        """Method which updates or sends a new player controller."""
        if self.updating:
            return

        self.updating = True

        if not self.controller:
            self.controller = InteractiveController(embed=self.build_embed(), player=self)
            await self.controller.start(self.context)

        elif not await self.is_position_fresh():
            try:
                await self.controller.message.delete()
            except disnake.HTTPException:
                pass

            self.controller.stop()

            self.controller = InteractiveController(embed=self.build_embed(), player=self)
            await self.controller.start(self.context)

        else:
            embed = self.build_embed()
            await self.controller.message.edit(content=None, embed=embed)

        self.updating = False

    def build_embed(self) -> typing.Optional[disnake.Embed]:
        """Method which builds our players controller embed."""
        track = self.current
        if not track:
            return

        channel = self.bot.get_channel(int(self.channel_id))
        qsize = self.queue.qsize()

        embed = disnake.Embed(title=f'Music Controller | {channel.name}', colour=disnake.Colour.random())
        embed.description = f'Now Playing:\n**`{track.title}`**\n\n'
        embed.set_thumbnail(url=track.thumb)

        embed.add_field(name='Duration', value=str(datetime.timedelta(milliseconds=int(track.length))))
        embed.add_field(name='Queue Length', value=str(qsize))
        embed.add_field(name='Volume', value=f'**`{self.volume}%`**')
        embed.add_field(name='Requested By', value=track.requester.mention)
        embed.add_field(name='DJ', value=self.dj.mention)
        embed.add_field(name='Video URL', value=f'[Click Here!]({track.uri})')

        return embed

    async def is_position_fresh(self) -> bool:
        """Method which checks whether the player controller should be remade or updated."""
        try:
            async for message in self.context.channel.history(limit=5):
                if message.id == self.controller.message.id:
                    return True
        except (disnake.HTTPException, AttributeError):
            return False

        return False

    async def teardown(self):
        """Clear internal states, remove player controller and disconnect."""
        try:
            await self.controller.message.delete()
        except disnake.HTTPException:
            pass

        self.controller.stop()

        try:
            await self.destroy()
        except KeyError:
            pass

    @property
    def loop(self):
        return self._loop

    @loop.setter
    def loop(self, value: bool = False):
        self._loop = value


class InteractiveController(Menu):
    """The Players interactive controller menu class."""

    def __init__(self, *, embed: disnake.Embed, player: Player):
        super().__init__(timeout=None)

        self.embed = embed
        self.player = player

    def update_context(self, payload: disnake.RawReactionActionEvent):
        """Update our context with the user who reacted."""
        ctx = copy.copy(self.ctx)
        ctx.author = payload.member

        return ctx

    def reaction_check(self, payload: disnake.RawReactionActionEvent):
        if payload.event_type == 'REACTION_REMOVE':
            return False

        if not payload.member:
            return False
        if payload.member.bot:
            return False
        if payload.message_id != self.message.id:
            return False
        if payload.member not in self.bot.get_channel(int(self.player.channel_id)).members:
            return False

        return payload.emoji in self.buttons

    async def send_initial_message(self, ctx: commands.Context, channel: disnake.TextChannel) -> disnake.Message:
        return await channel.send(embed=self.embed)

    @button(emoji='\u25B6')
    async def resume_command(self, payload: disnake.RawReactionActionEvent):
        """Resume button."""
        ctx = self.update_context(payload)

        command = self.bot.get_command('resume')
        ctx.command = command

        await self.bot.invoke(ctx)

    @button(emoji='\u23F8')
    async def pause_command(self, payload: disnake.RawReactionActionEvent):
        """Pause button"""
        ctx = self.update_context(payload)

        command = self.bot.get_command('pause')
        ctx.command = command

        await self.bot.invoke(ctx)

    @button(emoji='\u23F9')
    async def stop_command(self, payload: disnake.RawReactionActionEvent):
        """Stop button."""
        ctx = self.update_context(payload)

        command = self.bot.get_command('stop')
        ctx.command = command

        await self.bot.invoke(ctx)

    @button(emoji='\u23ED')
    async def skip_command(self, payload: disnake.RawReactionActionEvent):
        """Skip button."""
        ctx = self.update_context(payload)

        command = self.bot.get_command('skip')
        ctx.command = command

        await self.bot.invoke(ctx)

    @button(emoji='\U0001F500')
    async def shuffle_command(self, payload: disnake.RawReactionActionEvent):
        """Shuffle button."""
        ctx = self.update_context(payload)

        command = self.bot.get_command('shuffle')
        ctx.command = command

        await self.bot.invoke(ctx)

    @button(emoji='\u2795')
    async def volup_command(self, payload: disnake.RawReactionActionEvent):
        """Volume up button"""
        ctx = self.update_context(payload)

        command = self.bot.get_command('vol_up')
        ctx.command = command

        await self.bot.invoke(ctx)

    @button(emoji='\u2796')
    async def voldown_command(self, payload: disnake.RawReactionActionEvent):
        """Volume down button."""
        ctx = self.update_context(payload)

        command = self.bot.get_command('vol_down')
        ctx.command = command

        await self.bot.invoke(ctx)

    @button(emoji='\U0001F1F6')
    async def queue_command(self, payload: disnake.RawReactionActionEvent):
        """Player queue button."""
        ctx = self.update_context(payload)

        command = self.bot.get_command('queue')
        ctx.command = command

        await self.bot.invoke(ctx)


class PaginatorSource(ListPageSource):
    """Player queue paginator class."""

    def __init__(self, entries, *, per_page=8):
        super().__init__(entries, per_page=per_page)

    async def format_page(self, menu: Menu, page):
        embed = disnake.Embed(title='Coming Up...', colour=0x4f0321)
        embed.description = '\n'.join(f'`{index}. {title}`' for index, title in enumerate(page, 1))

        return embed

    def is_paginating(self):
        # We always want to embed even on 1 page of results...
        return True


class Music(commands.Cog, wavelink.WavelinkMixin):
    """Music Cog."""

    def __init__(self, bot: Bot):
        self.bot = bot

        if not hasattr(bot, 'wavelink'):
            bot.wavelink = wavelink.Client(bot=bot)

        bot.loop.create_task(self.start_nodes())

    async def start_nodes(self) -> None:
        """Connect and intiate nodes."""
        await self.bot.wait_until_ready()

        if self.bot.wavelink.nodes:
            previous = self.bot.wavelink.nodes.copy()

            for node in previous.values():
                await node.destroy()

        nodes = {'MAIN': {'host': '127.0.0.1',
                          'port': 2333,
                          'rest_uri': 'http://127.0.0.1:2333',
                          'password': 'youshallnotpass',
                          'identifier': 'MAIN',
                          'region': 'us_central'
                          }}

        for n in nodes.values():
            await self.bot.wavelink.initiate_node(**n)

    @wavelink.WavelinkMixin.listener()
    async def on_node_ready(self, node: wavelink.Node):
        print(f'Node {node.identifier} is ready!')

    @wavelink.WavelinkMixin.listener('on_track_stuck')
    @wavelink.WavelinkMixin.listener('on_track_end')
    @wavelink.WavelinkMixin.listener('on_track_exception')
    async def on_player_stop(self, node: wavelink.Node, payload):
        await payload.player.do_next()

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: disnake.Member, before: disnake.VoiceState,
                                    after: disnake.VoiceState):
        if member.bot:
            return

        player: Player = self.bot.wavelink.get_player(member.guild.id, cls=Player)

        if not player.channel_id or not player.context:
            player.node.players.pop(member.guild.id)
            return

        channel = self.bot.get_channel(int(player.channel_id))

        if member == player.dj and after.channel is None:
            for m in channel.members:
                if m.bot:
                    continue
                else:
                    player.dj = m
                    return

        elif after.channel == channel and player.dj not in channel.members:
            player.dj = member

    async def cog_command_error(self, ctx: commands.Context, error: Exception):
        """Cog wide error handler."""
        if isinstance(error, IncorrectChannelError):
            return

        if isinstance(error, NoChannelProvided):
            return await ctx.send(embed=disnake.Embed(
                description=f"You must be in a voice channel or provide one to connect to.",
                colour=disnake.Colour.random()))

    async def cog_before_invoke(self, ctx: commands.Context):
        """Coroutine called before command invocation.
        We mainly just want to check whether the user is in the players controller channel.
        """
        player: Player = self.bot.wavelink.get_player(ctx.guild.id, cls=Player, context=ctx)

        if player.context:
            if player.context.channel != ctx.channel:
                await ctx.send(
                    f'{ctx.author.mention}, you must be in {player.context.channel.mention} for this session.')
                raise IncorrectChannelError

        if ctx.command.name == 'connect' and not player.context:
            return
        elif self.is_privileged(ctx):
            return

        if not player.channel_id:
            return

        channel = self.bot.get_channel(int(player.channel_id))
        if not channel:
            return

        if player.is_connected:
            if ctx.author not in channel.members:
                await ctx.send(f'{ctx.author.mention}, you must be in `{channel.name}` to use voice commands.')
                raise IncorrectChannelError

    def required(self, ctx: commands.Context):
        """Method which returns required votes based on amount of members in a channel."""
        player: Player = self.bot.wavelink.get_player(guild_id=ctx.guild.id, cls=Player, context=ctx)
        channel = self.bot.get_channel(int(player.channel_id))
        required = math.ceil((len(channel.members) - 1) / 2.5)

        if ctx.command.name == 'stop':
            if len(channel.members) == 3:
                required = 2

        return required

    def is_privileged(self, ctx: commands.Context):
        """Check whether the user is an Admin or DJ."""
        player: Player = self.bot.wavelink.get_player(guild_id=ctx.guild.id, cls=Player, context=ctx)

        return player.dj == ctx.author or ctx.author.guild_permissions.kick_members

    @commands.command()
    async def connect(self, ctx: commands.Context, *,
                      channel: typing.Union[disnake.VoiceChannel, disnake.StageChannel] = None):
        """Connect to a voice channel."""
        player: Player = self.bot.wavelink.get_player(guild_id=ctx.guild.id, cls=Player, context=ctx)

        if player.is_connected:
            return

        channel = getattr(ctx.author.voice, 'channel', channel)
        if channel is None:
            raise NoChannelProvided

        await player.connect(channel.id)

    @commands.group(invoke_without_command=True, aliases=["yt"])
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def youtube(self, ctx, *, query):
        if re.search(r"^(https?\:\/\/)?((www\.)?youtube\.com|youtu\.?be)\/.+$", query):
            async with ctx.typing():
                query = (await youtube(query))["title"]

        async with ctx.typing():
            videos = (await (VideosSearch(query, limit=15)).next())["result"]

        if len(videos) == 0:
            return await ctx.reply("I could not find a video with that query", mention_author=False)

        embeds = []

        for video in videos:
            url = "https://www.youtube.com/watch?v=" + video["id"]
            channel_url = "https://www.youtube.com/channel/" + video["channel"]["id"]
            em = disnake.Embed(title=video["title"], url=url, color=disnake.Colour.random())
            em.add_field(name="Channel", value=f"[{video['channel']['name']}]({channel_url})", inline=True)
            em.add_field(name="Duration", value=video['duration'], inline=True)
            em.add_field(name="Views", value=video['viewCount']["text"])
            em.set_footer(
                text=f"Use the reactions for downloading • Page: {int(videos.index(video)) + 1}/{len(videos)}")
            em.set_thumbnail(url=video["thumbnails"][0]["url"])
            embeds.append(em)

        msg = await ctx.reply(embed=embeds[0], mention_author=False)

        page = 0

        reactions = [self.bot.icons["fulleft"], self.bot.icons["left"], self.bot.icons["right"],
                     self.bot.icons["fullright"], self.bot.icons["stop"]]

        for r in reactions:
            await msg.add_reaction(r)

        while True:
            try:
                done, pending = await asyncio.wait([
                    self.bot.wait_for("reaction_add", check=lambda reaction, user: str(
                        reaction.emoji) in reactions and user == ctx.author and reaction.message == msg, timeout=30),
                    self.bot.wait_for("reaction_remove", check=lambda reaction, user: str(
                        reaction.emoji) in reactions and user == ctx.author and reaction.message == msg, timeout=30)
                ], return_when=asyncio.FIRST_COMPLETED)
            except (asyncio.TimeoutError, asyncio.CancelledError):
                return

            try:
                reaction, user = done.pop().result()
            except (asyncio.TimeoutError, asyncio.CancelledError):
                return

            for future in pending:
                future.cancel()

            if str(reaction.emoji) == reactions[0]:
                if len(videos) != 1:
                    page = 0
                    await msg.edit(embed=embeds[page])

            elif str(reaction.emoji) == reactions[1]:
                if page != 0:
                    page -= 1
                    await msg.edit(embed=embeds[page])

            elif str(reaction.emoji) == reactions[2]:
                if len(videos) != 1:
                    page += 1
                    await msg.edit(embed=embeds[page])

            elif str(reaction.emoji) == reactions[3]:
                if page != len(videos):
                    page = len(videos) - 1
                    await msg.edit(embed=embeds[page])

            elif str(reaction.emoji) == reactions[4]:
                await msg.delete()
                break

    @youtube.command(aliases=["c"])
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def channel(self, ctx, *, query):
        async with ctx.typing():
            channels = (await (ChannelsSearch(query, limit=15, region="US")).next())["result"]

        if len(channels) == 0:
            return await ctx.reply(
                embed=disnake.Embed(title="Channel", description="I could not find a channel with that query.",
                                    color=disnake.Colour.random()))

        embeds = []

        for channel in channels:
            url = "https://www.youtube.com/channel/" + channel["id"]
            if not channel['thumbnails'][0]['url'].startswith("https:"):
                thumbnail = f"https:{channel['thumbnails'][0]['url']}"
            else:
                thumbnail = channel['thumbnails'][0]['url']
            if channel["descriptionSnippet"] is not None:
                em = disnake.Embed(title=channel["title"],
                                   description=" ".join(text["text"] for text in channel["descriptionSnippet"]),
                                   url=url, color=disnake.Colour.random())
            else:
                em = disnake.Embed(title=channel["title"], url=url, color=disnake.Colour.random())
            em.add_field(name="Videos",
                         value="".join(channel['videoCount'] if channel['videoCount'] is not None else "0"),
                         inline=True)
            em.add_field(name="Subscribers",
                         value="".join(channel['subscribers'] if channel['subscribers'] is not None else "0"),
                         inline=True)
            em.set_thumbnail(url=thumbnail)
            embeds.append(em)

        pag = await self.paginate(Paginator(embeds, per_page=1))
        await pag.start(ctx)

    @commands.command(aliases=['spot'])
    async def spotify(self, ctx, *, user: disnake.Member):
        if user is None:
            user = ctx.author
        else:
            try:
                user = await commands.MemberConverter().convert(ctx, str(user))
            except BaseException:
                raise disnake.ext.commands.MemberNotFound(str(user))
        activities = user.activities
        try:
            act = [
                activity for activity in activities if isinstance(
                    activity, disnake.Spotify)][0]
        except IndexError:
            return await ctx.send('No spotify was detected')
        start = humanize.naturaltime(disnake.utils.utcnow() - act.created_at)
        print(start)
        name = act.title
        art = " ".join(act.artists)
        album = act.album
        duration = round(((act.end - act.start).total_seconds() / 60), 2)
        min_sec = time.strftime("%M:%S", time.gmtime((act.end - act.start).total_seconds()))
        current = round(
            ((disnake.utils.utcnow() - act.start).total_seconds() / 60), 2)
        min_sec_current = time.strftime("%M:%S", time.gmtime(
            (disnake.utils.utcnow() - act.start).total_seconds()))
        embed = disnake.Embed(color=ctx.guild.me.color)
        embed.set_author(
            name=user.display_name,
            icon_url='https://netsbar.com/wp-content/uploads/2018/10/Spotify_Icon.png')
        embed.description = f"Listening To  [**{name}**] (https://open.spotify.com/track/{act.track_id})"
        embed.add_field(name="Artist", value=art, inline=True)
        embed.add_field(name="Album", value=album, inline=True)
        embed.set_thumbnail(url=act.album_cover_url)
        embed.add_field(name="Started Listening", value=start, inline=True)
        percent = int((current / duration) * 25)
        perbar = f"`{min_sec_current}`| {(percent - 1) * '─'}⚪️{(25 - percent) * '─'} | `{min_sec}`"
        embed.add_field(name="Progress", value=perbar)
        await ctx.send(embed=embed)

    @commands.command(aliases=['Latency'], name='Ping')
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def ping(self, ctx):
        msg = await ctx.send("Gathering Information...")
        times = []
        counter = 0
        embed = disnake.Embed(colour=disnake.Colour.random())
        for _ in range(3):
            counter += 1
            start = time.perf_counter()
            await msg.edit(content=f"Trying Ping{('.' * counter)} {counter}/3")
            end = time.perf_counter()
            speed = round((end - start) * 1000)
            times.append(speed)
            if speed < 160:
                embed.add_field(name=f"Ping {counter}:", value=f"🟢 | {speed}ms", inline=True)
            elif speed > 170:
                embed.add_field(name=f"Ping {counter}:", value=f"🟡 | {speed}ms", inline=True)
            else:
                embed.add_field(name=f"Ping {counter}:", value=f"🔴 | {speed}ms", inline=True)

        embed.add_field(name="Bot Latency", value=f"{round(self.bot.latency * 1000)}ms")
        embed.add_field(name="Normal Speed",
                        value=f"{round((round(sum(times)) + round(self.bot.latency * 1000)) / 4)}ms")

        embed.set_footer(text=f"Total estimated elapsed time: {round(sum(times))}ms")
        embed.set_author(name=ctx.me.display_name, icon_url=ctx.me.avatar)

        await msg.edit(content=f":ping_pong: **{round((round(sum(times)) + round(self.bot.latency * 1000)) / 4)}ms**",
                       embed=embed)

    @commands.command()
    async def play(self, ctx: commands.Context, *, query: str):
        """Play or queue a song with the given query."""
        player: Player = self.bot.wavelink.get_player(guild_id=ctx.guild.id, cls=Player, context=ctx)

        if not player.is_connected:
            await ctx.invoke(self.connect)

        query = query.strip('<>')
        if not URL_REG.match(query):
            query = f'ytsearch:{query}'

        tracks = await self.bot.wavelink.get_tracks(query)
        if not tracks:
            return await ctx.send(f"{self.bot.icons['redtick']} No songs were found with that query. Please try again.",
                                  delete_after=15)

        if isinstance(tracks, wavelink.TrackPlaylist):
            for track in tracks.tracks:
                track = Track(track.id, track.info, requester=ctx.author)
                await player.queue.put(track)

            await ctx.send(f'```ini\nAdded the playlist {tracks.data["playlistInfo"]["name"]}'
                           f' with {len(tracks.tracks)} songs to the queue.\n```', delete_after=15)
        else:
            track = Track(tracks[0].id, tracks[0].info, requester=ctx.author)
            await ctx.send(f'```ini\nAdded {track.title} to the Queue\n```', delete_after=15)
            await player.queue.put(track)

        if not player.is_playing:
            await player.do_next()

    @commands.command()
    async def pause(self, ctx: commands.Context):
        """Pause the currently playing song."""
        player: Player = self.bot.wavelink.get_player(guild_id=ctx.guild.id, cls=Player, context=ctx)

        if player.is_paused or not player.is_connected:
            return

        if self.is_privileged(ctx):
            await ctx.send(embed=disnake.Embed(
                description=f"{self.bot.icons['info']} An admin or DJ has paused the player.",
                color=disnake.Colour.random()), delete_after=10)
            player.pause_votes.clear()

            return await player.set_pause(True)

        required = self.required(ctx)
        player.pause_votes.add(ctx.author)

        if len(player.pause_votes) >= required:
            await ctx.send(embed=disnake.Embed(
                description=f"{self.bot.icons['greentick']} Vote to pause passed. Pausing player.",
                color=disnake.Colour.random()), delete_after=10)
            player.pause_votes.clear()
            await player.set_pause(True)
        else:
            await ctx.send(embed=disnake.Embed(
                description=f"{self.bot.icons['info']} {ctx.author.mention} has voted to pause the player.",
                color=disnake.Colour.random()), delete_after=15)

    @commands.command()
    async def resume(self, ctx: commands.Context):
        """Resume a currently paused player."""
        player: Player = self.bot.wavelink.get_player(guild_id=ctx.guild.id, cls=Player, context=ctx)

        if not player.is_paused or not player.is_connected:
            return

        if self.is_privileged(ctx):
            await ctx.send('An admin or DJ has resumed the player.', delete_after=10)
            player.resume_votes.clear()

            return await player.set_pause(False)

        required = self.required(ctx)
        player.resume_votes.add(ctx.author)

        if len(player.resume_votes) >= required:
            await ctx.send('Vote to resume passed. Resuming player.', delete_after=10)
            player.resume_votes.clear()
            await player.set_pause(False)
        else:
            await ctx.send(f'{ctx.author.mention} has voted to resume the player.', delete_after=15)

    @commands.command()
    async def skip(self, ctx: commands.Context):
        """Skip the currently playing song."""
        player: Player = self.bot.wavelink.get_player(guild_id=ctx.guild.id, cls=Player, context=ctx)

        if not player.is_connected:
            return

        if self.is_privileged(ctx):
            await ctx.send(embed=disnake.Embed(
                description=f"{self.bot.icons['info']} An admin or DJ has paused the player.",
                color=disnake.Colour.random()), delete_after=10)
            player.skip_votes.clear()

            return await player.stop()

        if ctx.author == player.current.requester:
            await ctx.send('The song requester has skipped the song.', delete_after=10)
            player.skip_votes.clear()

            return await player.stop()

        required = self.required(ctx)
        player.skip_votes.add(ctx.author)

        if len(player.skip_votes) >= required:
            await ctx.send('Vote to skip passed. Skipping song.', delete_after=10)
            player.skip_votes.clear()
            await player.stop()
        else:
            await ctx.send(embed=disnake.Embed(
                           description=f"{self.bot.icons['info']} `{ctx.author}` has voted to skip the song.",
                           color=disnake.Colour.random()), 
                           delete_after=15)

    @commands.command()
    async def stop(self, ctx: commands.Context):
        """Stop the player and clear all internal states."""
        player: Player = self.bot.wavelink.get_player(guild_id=ctx.guild.id, cls=Player, context=ctx)

        if not player.is_connected:
            return

        if self.is_privileged(ctx):
            await ctx.send(embed=disnake.Embed(
                description=f"{self.bot.icons['info']} An admin or DJ has stopped the player.",
                color=disnake.Colour.random()), delete_after=10)
            return await player.teardown()

        required = self.required(ctx)
        player.stop_votes.add(ctx.author)

        if len(player.stop_votes) >= required:
            await ctx.send('Vote to stop passed. Stopping the player.', delete_after=10)
            await player.teardown()
        else:
            await ctx.send(f'{ctx.author.mention} has voted to stop the player.', delete_after=15)

    @commands.command(aliases=['v', 'vol'])
    async def volume(self, ctx: commands.Context, *, vol: int):
        """Change the players volume, between 1 and 100."""
        player: Player = self.bot.wavelink.get_player(guild_id=ctx.guild.id, cls=Player, context=ctx)

        if not player.is_connected:
            return

        if not self.is_privileged(ctx):
            return await ctx.send('Only the DJ or admins may change the volume.')

        if not 0 < vol < 101:
            return await ctx.send('Please enter a value between 1 and 100.')

        await player.set_volume(vol)
        await ctx.send(f'Set the volume to **{vol}**%', delete_after=7)

    @commands.command(aliases=['mix'])
    async def shuffle(self, ctx: commands.Context):
        """Shuffle the players queue."""
        player: Player = self.bot.wavelink.get_player(guild_id=ctx.guild.id, cls=Player, context=ctx)

        if not player.is_connected:
            return

        if player.queue.qsize() < 3:
            return await ctx.send('Add more songs to the queue before shuffling.', delete_after=15)

        if self.is_privileged(ctx):
            await ctx.send('An admin or DJ has shuffled the playlist.', delete_after=10)
            player.shuffle_votes.clear()
            return random.shuffle(player.queue._queue)

        required = self.required(ctx)
        player.shuffle_votes.add(ctx.author)

        if len(player.shuffle_votes) >= required:
            await ctx.send('Vote to shuffle passed. Shuffling the playlist.', delete_after=10)
            player.shuffle_votes.clear()
            random.shuffle(player.queue._queue)
        else:
            await ctx.send(f"`{ctx.author}` has voted to shuffle the playlist.", delete_after=15)

    @commands.command(hidden=True)
    async def vol_up(self, ctx: commands.Context):
        """Command used for volume up button."""
        player: Player = self.bot.wavelink.get_player(guild_id=ctx.guild.id, cls=Player, context=ctx)

        if not player.is_connected or not self.is_privileged(ctx):
            return

        vol = int(math.ceil((player.volume + 10) / 10)) * 10

        if vol > 100:
            vol = 100
            await ctx.send(f"{self.bot.icons['info']} Maximum volume reached", delete_after=7)

        await player.set_volume(vol)

    @commands.command(hidden=True)
    async def vol_down(self, ctx: commands.Context):
        """Command used for volume down button."""
        player: Player = self.bot.wavelink.get_player(guild_id=ctx.guild.id, cls=Player, context=ctx)

        if not player.is_connected or not self.is_privileged(ctx):
            return

        vol = int(math.ceil((player.volume - 10) / 10)) * 10

        if vol < 0:
            vol = 0
            await ctx.send(embed=disnake.Embed(
                description=f"{self.bot.icons['info']} Player is currently muted", color=disnake.Colour.random())
                , delete_after=10)

        await player.set_volume(vol)

    @commands.command(aliases=['eq'])
    async def equalizer(self, ctx: commands.Context, *, equalizer: str):
        """Change the players equalizer."""
        player: Player = self.bot.wavelink.get_player(guild_id=ctx.guild.id, cls=Player, context=ctx)

        if not player.is_connected:
            return

        if not self.is_privileged(ctx):
            return await ctx.send(embed=disnake.Embed(
                description=f"{self.bot.icons['info']} Only the DJ or admins may change the equalizer.",
                color=disnake.Colour.random()))

        eqs = {'flat': wavelink.Equalizer.flat(),
               'boost': wavelink.Equalizer.boost(),
               'metal': wavelink.Equalizer.metal(),
               'piano': wavelink.Equalizer.piano()}

        eq = eqs.get(equalizer.lower(), None)

        if not eq:
            joined = "\n".join(eqs.keys())
            return await ctx.send(embed=disnake.Embed(
                description=f"{self.bot.icons['redtick']} Invalid EQ provided. Valid EQs:\n\n`{joined}`",
                color=disnake.Colour.random()))

        await ctx.send(f'Successfully changed equalizer to {equalizer}', delete_after=15)
        await player.set_eq(eq)

    @commands.command(aliases=['q', 'que'])
    async def queue(self, ctx: commands.Context):
        """Display the players queued songs."""
        player: Player = self.bot.wavelink.get_player(guild_id=ctx.guild.id, cls=Player, context=ctx)

        if not player.is_connected:
            return

        if player.queue.qsize() == 0:
            return await ctx.send(embed=disnake.Embed(description=f"{self.bot.icons['info']} There are no more songs "
                                                                  f"in the queue.", colour=disnake.Colour.random()),
                                  delete_after=15)

        entries = [track.title for track in player.queue._queue]
        pages = PaginatorSource(entries=entries)
        paginator = MenuPages(source=pages, timeout=None, delete_message_after=True)

        await paginator.start(ctx)

    @commands.command(aliases=['np', 'now_playing', 'current'])
    async def nowplaying(self, ctx: commands.Context):
        """Update the player controller."""
        player: Player = self.bot.wavelink.get_player(guild_id=ctx.guild.id, cls=Player, context=ctx)

        if not player.is_connected:
            return

        await player.invoke_controller()

    @commands.command(aliases=['swap'])
    async def swap_dj(self, ctx: commands.Context, *, member: disnake.Member = None):
        """Swap the current DJ to another member in the voice channel."""
        player: Player = self.bot.wavelink.get_player(guild_id=ctx.guild.id, cls=Player, context=ctx)

        if not player.is_connected:
            return

        if not self.is_privileged(ctx):
            return await ctx.send('Only admins and the DJ may use this command.', delete_after=15)

        members = self.bot.get_channel(int(player.channel_id)).members

        if member and member not in members:
            return await ctx.send(f'{member} is not currently in voice, so can not be a DJ.', delete_after=15)

        if member and member == player.dj:
            return await ctx.send('Cannot swap DJ to the current DJ... :)', delete_after=15)

        if len(members) <= 2:
            return await ctx.send('No more members to swap to.', delete_after=15)

        if member:
            player.dj = member
            return await ctx.send(f'{member.mention} is now the DJ.')

        for m in members:
            if m == player.dj or m.bot:
                continue
            else:
                player.dj = m
                return await ctx.send(f'{member.mention} is now the DJ.')


def setup(bot: commands.Bot):
    bot.add_cog(Music(bot))
