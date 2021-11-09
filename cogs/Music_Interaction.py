from youtubesearchpython.__future__ import ChannelsSearch, VideosSearch
import traceback
import pathlib
import sys
import psutil
from loguru import logger
from disnake.ext.commands.params import Param
import datetime
import math
import re
import time
import typing
import disnake
import humanize
import youtube_dl as ydl
from disnake.ext import commands
import wavelink
from MusicBot import Bot
from bot_utils.MusicPlayerInteraction import Player, Track
from bot_utils.paginator import SimpleEmbedPages
from jishaku.functools import executor_function

youtube_url_regex = re.compile(r'https?://(?:www\.)?.+')


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


class Music(commands.Cog, wavelink.WavelinkMixin):
    """Your friendly music bot"""

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
                          },
                 'Lavalink': {
                     'host': 'lava.link',
                     'port': 80,
                     'rest_uri': 'http://lava.link:80',
                     'password': '',
                     'identifier': 'Lavalink',
                     'region': 'us_central'
                 }}  # Lava.link is a public Lavalink node that you can connect to.

        for n in nodes.values():
            await self.bot.wavelink.initiate_node(**n)

    @wavelink.WavelinkMixin.listener()
    async def on_node_ready(self, node: wavelink.Node):
        logger.info(f'Node {node.identifier} is running!', __name="Music Bot")

    @wavelink.WavelinkMixin.listener('on_track_stuck')
    @wavelink.WavelinkMixin.listener('on_track_end')
    @wavelink.WavelinkMixin.listener('on_track_exception')
    async def on_player_stop(self, node: wavelink.Node, payload):
        await payload.player.play_next_song()

    @commands.Cog.listener("on_voice_state_update")
    async def DJ_assign(self, member: disnake.Member, before: disnake.VoiceState,
                        after: disnake.VoiceState):
        """Assign DJ role to the user who is currently playing music."""
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

    async def cog_slash_command_error(self, ctx: disnake.ApplicationCommandInteraction, error: Exception) -> None:
        """Cog wide error handler."""
        if ctx.response.is_done():
            safe_send = ctx.followup.send
        else:
            safe_send = ctx.response.send_message
        if isinstance(error, IncorrectChannelError):
            return

        if isinstance(error, NoChannelProvided):
            return await safe_send(embed=disnake.Embed(
                description=f"{self.bot.icons['redtick']} `You must be connected to a voice channel.`",
                colour=disnake.Colour.random()))

        # ignore all other exception types, but print them to stderr
        else:
            error_msg = "".join(traceback.format_exception(type(error), error, error.__traceback__))
            await safe_send(embed=disnake.Embed(
                description=f"**Error invoked by: {str(ctx.author)}**\nCommand: {ctx.application_command.name}\nError: "
                            f"```py\n{error_msg}```",
                color=disnake.Colour.random()))

            print(f"Ignoring exception in command {ctx.application_command}: ", file=sys.stderr)
            traceback.print_exception(type(error), error, error.__traceback__, file=sys.stderr)

    async def cog_slash_before_invoke(self, ctx: disnake.ApplicationCommandInteraction):
        """Cog wide before slash command invoke handler."""
        if ctx.response.is_done():
            safe_send = ctx.followup.send
        else:
            safe_send = ctx.response.send_message

        music_player: Player = self.bot.wavelink.get_player(ctx.guild.id, cls=Player, context=ctx)

        if music_player.context:
            if music_player.context.channel != ctx.channel:
                await ctx.response.send_message(
                    f'{ctx.author.mention}, you must be in {music_player.context.channel.mention} for this session.')
                raise IncorrectChannelError

        if ctx.application_command.name == 'connect' and not music_player.context:
            return
        elif self.is_author(ctx):
            return

        if not music_player.channel_id:
            return

        channel = self.bot.get_channel(int(music_player.channel_id))
        if not channel:
            return

        if music_player.is_connected:
            if ctx.author not in channel.members:
                await safe_send(embed=disnake.Embed(
                    description=f"{self.bot.icons['info']} You must be in `{channel.name}` to use voice commands."
                    , colour=disnake.Colour.random()))
                raise IncorrectChannelError

    def vote_check(self, ctx: disnake.ApplicationCommandInteraction):
        """Returns required votes based on amount of members in a channel."""
        player: Player = self.bot.wavelink.get_player(guild_id=ctx.guild.id, cls=Player, context=ctx)
        channel = self.bot.get_channel(int(player.channel_id))
        required = math.ceil((len(channel.members) - 1) / 2.5)

        if ctx.application_command.name == 'stop':
            if len(channel.members) == 3:
                required = 2

        return required

    def is_author(self, ctx: disnake.ApplicationCommandInteraction):
        """Check whether the user is the command invoker / ctx.author`."""
        player: Player = self.bot.wavelink.get_player(guild_id=ctx.guild.id, cls=Player, context=ctx)

        return player.dj == ctx.author or ctx.author.guild_permissions.kick_members

    async def connect(self, ctx: disnake.ApplicationCommandInteraction,
                      channel: typing.Union[disnake.VoiceChannel,
                                            disnake.StageChannel] = None) -> None:
        """Connect to a voice channel."""

        music_player: Player = self.bot.wavelink.get_player(guild_id=ctx.guild.id, cls=Player, context=ctx)

        if music_player.is_connected:
            return

        channel = getattr(ctx.author.voice, 'channel', channel)
        if channel is None:
            raise NoChannelProvided

        await music_player.connect(channel.id)
        await ctx.channel.send(
            embed=disnake.Embed(title=f":zzz: Joined in {channel}",
                                color=disnake.Colour.random()).set_footer(text=f"Requested by {ctx.author.name}"))

    @commands.slash_command()
    async def youtube(self, ctx: disnake.ApplicationCommandInteraction):
        pass

    @youtube.sub_command(description="Search youtube videos")
    async def video(self, ctx: disnake.ApplicationCommandInteraction, query: str = Param(description="Video Query")):
        await ctx.response.defer()
        if re.search(r"^(https?\:\/\/)?((www\.)?youtube\.com|youtu\.?be)\/.+$", query):
            async with ctx.channel.typing():
                query = (await youtube(query))["title"]

        async with ctx.channel.typing():
            videos = (await (VideosSearch(query, limit=15)).next())["result"]

        if len(videos) == 0:
            return await ctx.response.send_message("I could not find a video with that query")

        embeds = []

        for video in videos:
            url = "https://www.youtube.com/watch?v=" + video["id"]
            channel_url = "https://www.youtube.com/channel/" + video["channel"]["id"]
            em = disnake.Embed(title=video["title"], url=url, color=disnake.Colour.random())
            em.add_field(name="Channel", value=f"[{video['channel']['name']}]({channel_url})", inline=True)
            em.add_field(name="Duration", value=humanize.intword(video['duration']), inline=True)
            em.add_field(name="Views", value=humanize.intword(video['viewCount']["text"]))
            em.set_footer(
                text=f"Use the buttons for navigating • Page: {int(videos.index(video)) + 1}/{len(videos)}")
            em.set_thumbnail(url=video["thumbnails"][0]["url"])
            embeds.append(em)

        pag = SimpleEmbedPages(entries=embeds, ctx=ctx)
        await pag.start()

    @youtube.sub_command(description="Search youtube channels")
    async def channel(self, ctx: disnake.ApplicationCommandInteraction,
                      query: str = Param(description="Channel Query")):

        async with ctx.channel.typing():
            channels = (await (ChannelsSearch(query, limit=15, region="US")).next())["result"]

        if len(channels) == 0:
            return await ctx.response.send_message(
                embed=disnake.Embed(title="Channel", description="I could not find a channel with that query.",
                                    color=disnake.Colour.random()))

        await ctx.response.defer()

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

        pag = SimpleEmbedPages(entries=embeds, ctx=ctx)
        await pag.start()

    @commands.slash_command(description="Shows you spotify song information of an user's spotify rich presence")
    async def spotify(self, ctx: disnake.ApplicationCommandInteraction,
                      user: disnake.Member = Param(description="Member Query")):
        activities = user.activities
        try:
            act = [
                activity for activity in activities if isinstance(
                    activity, disnake.Spotify)][0]
        except IndexError:
            return await ctx.channel.send('No spotify was detected')
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
        await ctx.channel.send(embed=embed)

    @commands.slash_command(description="Shows bot latency.")
    async def ping(self, ctx: disnake.ApplicationCommandInteraction):
        await ctx.response.send_message("Gathering Information...")
        times = []
        counter = 0
        embed = disnake.Embed(colour=disnake.Colour.random())
        for _ in range(3):
            counter += 1
            start = time.perf_counter()
            await ctx.edit_original_message(content=f"Trying Ping{('.' * counter)} {counter}/3")
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
        embed.set_author(name=ctx.me.display_name, icon_url=ctx.me.avatar.url)

        await ctx.edit_original_message(
            content=f":ping_pong: **{round((round(sum(times)) + round(self.bot.latency * 1000)) / 4)}ms**",
            embed=embed)

    @commands.slash_command(description="Play or queue a song with the given query")
    async def play(self, ctx: disnake.ApplicationCommandInteraction, query: str = Param(description="Song search")):
        player: Player = self.bot.wavelink.get_player(guild_id=ctx.guild.id, cls=Player, context=ctx)
        await ctx.response.defer()

        if not player.is_connected:
            await self.connect(ctx=ctx)

        query = query.strip('<>')
        if not youtube_url_regex.match(query):
            query = f'ytsearch:{query}'

        tracks = await self.bot.wavelink.get_tracks(query)
        if not tracks:
            return await ctx.edit_original_message(content=
                                                   f"{self.bot.icons['redtick']} No songs were found with that query. "
                                                   f"Please try again.",
                                                   )

        if isinstance(tracks, wavelink.TrackPlaylist):
            for track in tracks.tracks:
                track = Track(track.id, track.info, requester=ctx.author)
                await player.queue.put(track)

            await ctx.channel.send(f'```ini\nAdded the playlist {tracks.data["playlistInfo"]["name"]}'
                                   f' with {len(tracks.tracks)} songs to the queue.\n```', )
        else:
            track = Track(tracks[0].id, tracks[0].info, requester=ctx.author)
            await ctx.edit_original_message(
                content=f"\n{self.bot.icons['headphones']} Enqueued `{track.title}` to the Queue\n")
            await player.queue.put(track)

        if not player.is_playing:
            await player.play_next_song()

    @commands.slash_command(description="Pause the currently playing song.")
    async def pause(self, ctx: disnake.ApplicationCommandInteraction):
        player: Player = self.bot.wavelink.get_player(guild_id=ctx.guild.id, cls=Player, context=ctx)

        if not player.is_connected:
            return await ctx.response.send_message(embed=disnake.Embed(
                description=f"{self.bot.icons['redtick']} `You must be connected to a voice channel.`",
                colour=disnake.Colour.random()), delete_after=10)

        if player.is_paused:
            return await ctx.response.send_message(embed=disnake.Embed(
                description=f"{self.bot.icons['redtick']} `The player is already paused.`",
                colour=disnake.Colour.random()), delete_after=10)

        if self.is_author(ctx):
            await ctx.response.send_message(embed=disnake.Embed(
                description=f"{self.bot.icons['info']} Alright I have paused the player.",
                color=disnake.Colour.random()), delete_after=10)
            player.pause_votes.clear()

            return await player.set_pause(True)

        required = self.vote_check(ctx)
        player.pause_votes.add(ctx.author)

        if len(player.pause_votes) >= required:
            await ctx.response.send_message(embed=disnake.Embed(
                description=f"{self.bot.icons['greentick']} Vote to pause passed. Pausing player.",
                color=disnake.Colour.random()), delete_after=10)
            player.pause_votes.clear()
            await player.set_pause(True)
        else:
            await ctx.response.send_message(embed=disnake.Embed(
                description=f"{self.bot.icons['info']} {ctx.author.mention} has voted to pause the player.",
                color=disnake.Colour.random()), )

    @commands.slash_command(description="Resumes a currently paused song.")
    async def resume(self, ctx: disnake.ApplicationCommandInteraction):
        player: Player = self.bot.wavelink.get_player(guild_id=ctx.guild.id, cls=Player, context=ctx)

        if not player.is_connected:
            return await ctx.response.send_message(embed=disnake.Embed(
                description=f"{self.bot.icons['redtick']} `You must be connected to a voice channel.`",
                colour=disnake.Colour.random()), delete_after=10)

        if not player.is_paused:
            return await ctx.response.send_message(embed=disnake.Embed(
                description=f"{self.bot.icons['redtick']} `The player is not paused.`",
                colour=disnake.Colour.random()), delete_after=10)

        if self.is_author(ctx):
            await ctx.response.send_message(embed=disnake.Embed(
                description=f"{self.bot.icons['info']} Alright I have resumed this song.",
                color=disnake.Colour.random()), delete_after=10)
            player.resume_votes.clear()

            return await player.set_pause(False)

        required = self.vote_check(ctx)
        player.resume_votes.add(ctx.author)

        if len(player.resume_votes) >= required:
            await ctx.response.send_message("Vote to resume passed. Resuming player.", delete_after=10)
            player.resume_votes.clear()
            await player.set_pause(False)
        else:
            await ctx.response.send_message(f'{ctx.author} has voted to resume the song.', )

    @commands.slash_command(description="Skip the currently playing song.")
    async def skip(self, ctx: disnake.ApplicationCommandInteraction):
        player: Player = self.bot.wavelink.get_player(guild_id=ctx.guild.id, cls=Player, context=ctx)

        if not player.is_connected:
            return await ctx.response.send_message(embed=disnake.Embed(
                description=f"{self.bot.icons['redtick']} `You must be connected to a voice channel.`",
                colour=disnake.Colour.random()), delete_after=10)

        if self.is_author(ctx):
            await ctx.response.send_message(embed=disnake.Embed(
                description=f"{self.bot.icons['info']} `{ctx.author}` has paused the player.",
                color=disnake.Colour.random()), delete_after=10)
            player.skip_votes.clear()

            return await player.stop()

        if ctx.author == player.current.requester:
            await ctx.response.send_message(embed=disnake.Embed(
                description=f"{self.bot.icons['info']} `{ctx.author}` has skipped the song.",
                color=disnake.Colour.random()))
            player.skip_votes.clear()

            return await player.stop()

        required = self.vote_check(ctx)
        player.skip_votes.add(ctx.author)

        if len(player.skip_votes) >= required:
            await ctx.response.send_message('Vote to skip passed. Skipping song.', delete_after=10)
            player.skip_votes.clear()
            await player.stop()
        else:
            await ctx.response.send_message(embed=disnake.Embed(
                description=f"{self.bot.icons['info']} `{ctx.author}` has voted to skip the song.",
                color=disnake.Colour.random()),
            )

    @commands.slash_command(description="Stop the currently playing song and the music player.")
    async def stop(self, ctx: disnake.ApplicationCommandInteraction):
        player: Player = self.bot.wavelink.get_player(guild_id=ctx.guild.id, cls=Player, context=ctx)

        if not player.is_connected:
            return await ctx.response.send_message(embed=disnake.Embed(
                description=f"{self.bot.icons['redtick']} `You must be connected to a voice channel.`",
                colour=disnake.Colour.random()), delete_after=10)

        if self.is_author(ctx):
            await ctx.response.send_message(embed=disnake.Embed(
                description=f"{self.bot.icons['info']} `{ctx.author}` has stopped the player.",
                color=disnake.Colour.random()), delete_after=10)
            return await player.teardown()

        required = self.vote_check(ctx)
        player.stop_votes.add(ctx.author)

        if len(player.stop_votes) >= required:
            await ctx.response.send_message(embed=disnake.Embed(
                description=f"{self.bot.icons['info']} Vote passed, stopping the player.",
                color=disnake.Colour.random()))
            await player.teardown()
        else:
            await ctx.response.send_message(embed=disnake.Embed(
                description=f"{self.bot.icons['info']} `{ctx.author}` has voted to skip the song.",
                color=disnake.Colour.random()))

    @commands.slash_command(description="Change the players volume, between 1 and 100.")
    async def volume(self, ctx: disnake.ApplicationCommandInteraction,
                     vol: int = Param(description="The volume to set the player to.", gt=1, lt=100)):
        player: Player = self.bot.wavelink.get_player(guild_id=ctx.guild.id, cls=Player, context=ctx)

        if not player.is_connected:
            return await ctx.response.send_message(embed=disnake.Embed(
                description=f"{self.bot.icons['redtick']} `You must be connected to a voice channel.`",
                colour=disnake.Colour.random()))

        if not self.is_author(ctx):
            return await ctx.response.send_message(embed=disnake.Embed(
                description=f"{self.bot.icons['info']} Only the `{ctx.author}` can change the volume of this song.",
                color=disnake.Colour.random()))

        if not 0 < vol < 101:
            return await ctx.response.send(f"{self.bot.icons['info']} Please enter a value between 1 and 100.")

        await player.set_volume(vol)
        await ctx.response.send_message(f'Set the volume to **{vol}**%')

    @commands.slash_command(description="Loops the current playing track.")
    async def loop(self, ctx: disnake.ApplicationCommandInteraction):
        player: Player = self.bot.wavelink.get_player(guild_id=ctx.guild.id, cls=Player, context=ctx)

        if not player.is_connected:
            return await ctx.response.send_message(embed=disnake.Embed(
                description=f"{self.bot.icons['redtick']} `You must be connected to a voice channel.`",
                colour=disnake.Colour.random()), delete_after=10)

        if not self.is_author(ctx):
            return await ctx.response.send_message(embed=disnake.Embed(
                description=f"{self.bot.icons['info']} Only the `{ctx.author}` can loop this song.",
                color=disnake.Colour.random()))

        if player.loop is False:
            await ctx.response.send_message(embed=disnake.Embed(
                description=f"{self.bot.icons['greentick']} Looped the current track.",
                color=disnake.Colour.random()))
            player.loop = True
            return
        if player.loop is True:
            await ctx.response.send_message(embed=disnake.Embed(
                description=f"{self.bot.icons['greentick']} Un-looped the current track.",
                color=disnake.Colour.random()))
            player.loop = False
            return

    @commands.slash_command(description="Shuffle the players queue.")
    async def shuffle(self, ctx: disnake.ApplicationCommandInteraction):
        player: Player = self.bot.wavelink.get_player(guild_id=ctx.guild.id, cls=Player, context=ctx)

        if not player.is_connected:
            return await ctx.response.send_message(embed=disnake.Embed(
                description=f"{self.bot.icons['redtick']} `You must be connected to a voice channel.`",
                colour=disnake.Colour.random()), delete_after=10)

        if player.queue.qsize() < 3:
            return await ctx.response.send_message(embed=disnake.Embed(
                description=f"{self.bot.icons['info']} Add more songs before shuffling.",
                color=disnake.Colour.random()))

        if self.is_author(ctx):
            await ctx.channel.send(embed=disnake.Embed(
                description=f"{self.bot.icons['info']} `{ctx.author}` has shuffled the queue.",
                color=disnake.Colour.random()))

            player.shuffle_votes.clear()
            return player.queue.shuffle()

        required = self.vote_check(ctx)
        player.shuffle_votes.add(ctx.author)

        if len(player.shuffle_votes) >= required:
            await ctx.channel.send(embed=disnake.Embed(
                description=f"{self.bot.icons['info']} Vote passed, shuffling songs.",
                color=disnake.Colour.random()))

            player.shuffle_votes.clear()
            player.queue.shuffle()
        else:
            return await ctx.channel.send(embed=disnake.Embed(
                description=f"{self.bot.icons['info']} `{ctx.author}` has voted to shuffle the queue.",
                color=disnake.Colour.random()))

    @commands.slash_command(description="Clears the entire queue.")
    async def clearqueue(self, ctx: disnake.ApplicationCommandInteraction):
        player: Player = self.bot.wavelink.get_player(guild_id=ctx.guild.id, cls=Player, context=ctx)

        if not player.is_connected:
            return await ctx.response.send_message(embed=disnake.Embed(
                description=f"{self.bot.icons['redtick']} `You must be connected to a voice channel.`",
                colour=disnake.Colour.random()), delete_after=10)

        if player.queue.qsize() == 0:
            return await ctx.response.send_message(embed=disnake.Embed(
                description=f"{self.bot.icons['info']} Queue is empty.",
                color=disnake.Colour.random()))

        if self.is_author(ctx):
            await ctx.response.send_message(embed=disnake.Embed(
                description=f"{self.bot.icons['info']} `{ctx.author}` has cleared the queue.",
                color=disnake.Colour.random()))

            player.clear_votes.clear()
            player.queue.clear()

        required = self.vote_check(ctx)
        player.clear_votes.add(ctx.author)

        if len(player.shuffle_votes) >= required:
            await ctx.response.send_message(embed=disnake.Embed(
                description=f"{self.bot.icons['info']} Vote passed, clearing the queue.",
                color=disnake.Colour.random()))

            player.clear_votes.clear()
            player.queue.clear()
        else:
            return await ctx.response.send_message(embed=disnake.Embed(
                description=f"{self.bot.icons['info']} `{ctx.author}` has voted to clear the queue.",
                color=disnake.Colour.random()))

    @commands.slash_command(description="Retrieve various Node/Server/Player information.")
    async def wavelink_information(self, ctx: disnake.ApplicationCommandInteraction):
        player: Player = self.bot.wavelink.get_player(guild_id=ctx.guild.id, cls=Player, context=ctx)
        node = player.node

        used = humanize.naturalsize(node.stats.memory_used)
        total = humanize.naturalsize(node.stats.memory_allocated)
        free = humanize.naturalsize(node.stats.memory_free)
        cpu = node.stats.cpu_cores

        fmt = f'**WaveLink:** `{wavelink.__version__}`\n\n' \
              f'Connected to `{len(self.bot.wavelink.nodes)}` nodes.\n' \
              f'Best available Node `{self.bot.wavelink.get_best_node().__repr__()}`\n' \
              f'`{len(self.bot.wavelink.players)}` players are distributed on nodes.\n' \
              f'`{node.stats.players}` players are distributed on server.\n' \
              f'`{node.stats.playing_players}` players are playing on server.\n\n' \
              f'Server Memory: `{used}/{total}` | `({free} free)`\n' \
              f'Server CPU: `{cpu}`\n\n' \
              f'Server Uptime: `{datetime.timedelta(milliseconds=node.stats.uptime)}`'
        await ctx.response.send_message(embed=disnake.Embed(
            description=fmt, color=disnake.Colour.random()).set_footer(text=f"Requested by {ctx.author}",
                                                                       icon_url=ctx.author.avatar.url))

    @commands.slash_command(description="Change the players equalizer.")
    async def equalizer(self, ctx: disnake.ApplicationCommandInteraction,
                        equalizer: str = Param(description="Your equalizer")):
        player: Player = self.bot.wavelink.get_player(guild_id=ctx.guild.id, cls=Player, context=ctx)

        if not player.is_connected:
            return await ctx.response.send_message(embed=disnake.Embed(
                description=f"{self.bot.icons['redtick']} `You must be connected to a voice channel.`",
                colour=disnake.Colour.random()))

        if not self.is_author(ctx):
            return await ctx.response.send_message(embed=disnake.Embed(
                description=f"{self.bot.icons['info']} Only the `{ctx.author}` can change the equalizer.",
                color=disnake.Colour.random()))

        eqs = {'flat': wavelink.Equalizer.flat(),
               'boost': wavelink.Equalizer.boost(),
               'metal': wavelink.Equalizer.metal(),
               'piano': wavelink.Equalizer.piano()
               }  # you can make your own custom equalizers and pass it here.

        eq = eqs.get(equalizer.lower(), None)

        if not eq:
            joined = "\n".join(eqs.keys())
            return await ctx.response.send_message(embed=disnake.Embed(
                description=f"{self.bot.icons['redtick']} Invalid EQ provided. Valid EQs:\n\n`{joined}`",
                color=disnake.Colour.random()))

        await ctx.response.send_message(embed=
                                        disnake.Embed(description=f"{self.bot.icons['greentick']} Successfully "
                                                                  f"changed equalizer to `{equalizer}`",
                                                      colour=disnake.Colour.random()))
        await player.set_eq(eq)

    @commands.slash_command(description="Create and set your own equalizer.")
    async def customequalizer(self, ctx: disnake.ApplicationCommandInteraction,
                              equalizer: str = Param(description="Your equalizer name"),
                              levels: str = Param(description="Your equalizer levels in a list.")):
        player: Player = self.bot.wavelink.get_player(guild_id=ctx.guild.id, cls=Player, context=ctx)

        if not player.is_connected:
            return await ctx.response.send_message(embed=disnake.Embed(
                description=f"{self.bot.icons['redtick']} `You must be connected to a voice channel.`",
                colour=disnake.Colour.random()), delete_after=10)

        if not self.is_author(ctx):
            return await ctx.response.send_message(embed=disnake.Embed(
                description=f"{self.bot.icons['info']} Only the `{ctx.author}` can change the equalizer.",
                color=disnake.Colour.random()))

        eq = wavelink.Equalizer.build(levels=list(levels), name=equalizer)

        await ctx.response.send_message(embed=
                                        disnake.Embed(description=f"{self.bot.icons['greentick']} Successfully "
                                                                  f"changed equalizer to `{equalizer}`",
                                                      colour=disnake.Colour.random()))
        await player.set_eq(eq)

    @commands.slash_command(description="Display the player's queued songs.")
    async def queue(self, ctx: disnake.ApplicationCommandInteraction):
        player: Player = self.bot.wavelink.get_player(guild_id=ctx.guild.id, cls=Player, context=ctx)

        if not player.is_connected:
            return await ctx.response.send_message(embed=disnake.Embed(
                description=f"{self.bot.icons['redtick']} `You must be connected to a voice channel.`",
                colour=disnake.Colour.random()), delete_after=10)

        if player.queue.qsize() == 0:
            return await ctx.response.send_message(
                embed=disnake.Embed(description=f"{self.bot.icons['info']} There are no more songs "
                                                f"in the queue.", colour=disnake.Colour.random()),
            )
        await ctx.response.defer()

        entries = []
        for track in player.queue._queue:
            embed = disnake.Embed(title=f"`{len(player.queue._queue)}` tracks in queue....",
                                  color=disnake.Colour.random())
            embed.add_field(name=f"{track.title}", value=track.uri, inline=False)
            entries.append(embed)

        paginator = SimpleEmbedPages(entries=entries, ctx=ctx)

        await paginator.start()

    @commands.slash_command(description="Show the current playing song")
    async def nowplaying(self, ctx: disnake.ApplicationCommandInteraction):
        player: Player = self.bot.wavelink.get_player(guild_id=ctx.guild.id, cls=Player, context=ctx)

        if not player.is_connected:
            return await ctx.response.send_message(embed=disnake.Embed(
                description=f"{self.bot.icons['redtick']} `You must be connected to a voice channel.`",
                colour=disnake.Colour.random()))

        embed = await player.make_song_embed()  # shows the song embed.
        await ctx.response.send_message(embed=embed)

    @commands.slash_command(description="Save the current playing song in your dms.")
    async def save(self, ctx: disnake.ApplicationCommandInteraction):
        player: Player = self.bot.wavelink.get_player(guild_id=ctx.guild.id, cls=Player, context=ctx)

        if not player.is_connected:
            return await ctx.response.send_message(embed=disnake.Embed(
                description=f"{self.bot.icons['redtick']} `You must be connected to a voice channel.`",
                colour=disnake.Colour.random()))

        await player.make_song_embed()  # shows the song embed.
        await ctx.author.response.send_message(embed=disnake.Embed)

    @commands.slash_command(description="Seek to a specific time in the song.")
    async def seek(self, ctx: disnake.ApplicationCommandInteraction, position: str = Param(description="The position "
                                                                                                       "to seek to")):
        player: Player = self.bot.wavelink.get_player(guild_id=ctx.guild.id, cls=Player, context=ctx)
        time_regex = r"([0-9]{1,2})[:ms](([0-9]{1,2})s?)?"

        if not player.is_paused or not player.is_connected:
            return

        if not (match := re.match(time_regex, position)):
            raise commands.BadArgument(f"{position} is not a valid time.")
        if match.group(3):
            secs = (int(match.group(1)) * 60) + (int(match.group(3)))
        else:
            secs = int(match.group(1))

        await player.seek(secs * 1000)
        await ctx.response.send_message(embed=disnake.Embed(
            description=f"{self.bot.icons['greentick']} Successfully seeked."))

    @commands.slash_command(description="Swap the current DJ to another member in the voice channel.", aliases=['swap'])
    async def swap_dj(self, ctx: disnake.ApplicationCommandInteraction,
                      member: disnake.Member = Param(description="The member to swap to")):
        player: Player = self.bot.wavelink.get_player(guild_id=ctx.guild.id, cls=Player, context=ctx)

        if not player.is_connected:
            return await ctx.response.send_message(embed=disnake.Embed(
                description=f"{self.bot.icons['redtick']} `You must be connected to a voice channel.`",
                colour=disnake.Colour.random()))

        if not self.is_author(ctx):
            return await ctx.channel.send(embed=disnake.Embed(
                description=f"Only admins and the DJ can use this command.",
                color=disnake.Colour.random()))

        members = self.bot.get_channel(int(player.channel_id)).members

        if member and member not in members:
            return await ctx.channel.send(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['info']} `{member}` is not currently in voice, so they cannot be a DJ.")
                , )

        if member and member == player.dj:
            return await ctx.channel.send("Cannot swap DJ to the current DJ... :)", )

        if len(members) <= 2:
            return await ctx.channel.send(embed=disnake.Embed(
                description=f"{self.bot.icons['redtick']} `{member}` No more members to swap to."),
                color=disnake.Colour.red())

        if member:
            player.dj = member
            return await ctx.channel.send(embed=disnake.Embed(
                description=f"{self.bot.icons['info']} `{member}` is now a DJ.")
                , )

        for m in members:
            if m == player.dj or m.bot:
                continue
            else:
                player.dj = m
                return await ctx.channel.send(embed=disnake.Embed(
                    description=f"{self.bot.icons['info']} `{member}` is now a DJ.", colour=0x00ff00))

    @commands.slash_command(description="Shows information about the bot.")
    async def info(self, ctx: disnake.ApplicationCommandInteraction):
        await ctx.response.defer()
        async with ctx.channel.typing():
            process = psutil.Process()
            version = sys.version_info
            em = disnake.Embed(color=disnake.Colour.random())

            # File Stats
            def line_count():
                files = classes = funcs = comments = lines = letters = 0
                p = pathlib.Path('./')
                for f in p.rglob("*.py"):
                    files += 1
                    with f.open() as of:
                        letters = sum(len(f.open().read()) for f in p.rglob("*.py"))
                        for line in of.readlines():
                            line = line.strip()
                            if line.startswith("class"):
                                classes += 1
                            if line.startswith("def"):
                                funcs += 1
                            if line.startswith("async def"):
                                funcs += 1
                            if "#" in line:
                                comments += 1
                            lines += 1
                return files, classes, funcs, comments, lines, letters

            files, classes, funcs, comments, lines, letters = await self.bot.loop.run_in_executor(None, line_count)
            #
            em.add_field(name="Bot", value=f"""
       {self.bot.icons['arrow']} **Guilds**: `{len(self.bot.guilds)}`
       {self.bot.icons['arrow']} **Users**: `{len(self.bot.users)}`
       {self.bot.icons['arrow']} **Commands**: `{len([cmd for cmd in list(self.bot.walk_commands()) if not cmd.hidden])}`""",
                         inline=True)
            em.add_field(name="File Statistics", value=f"""
       {self.bot.icons['arrow']} **Letters**: `{letters}`
       {self.bot.icons['arrow']} **Files**: `{files}`
       {self.bot.icons['arrow']} **Lines**: `{lines}`
       {self.bot.icons['arrow']} **Functions**: `{funcs}`""", inline=True)
            em.add_field(name="Developers", value=f"""
       {self.bot.icons['arrow']} `KortaPo#5915`""", inline=True)
            em.set_thumbnail(url=self.bot.user.avatar.url)
        em.set_footer(text=f"Python {version[0]}.{version[1]}.{version[2]} • disnake {disnake.__version__}")
        await ctx.edit_original_message(embed=em)


def setup(bot):
    bot.add_cog(Music(bot))
