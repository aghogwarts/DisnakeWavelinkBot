from youtubesearchpython.__future__ import ChannelsSearch, VideosSearch

import math
import re
import sys
import traceback
import typing

import disnake
import humanize
import youtube_dl as ydl
from disnake.ext import commands
from disnake.ext.commands.params import Param

import wavelink
from MusicBot import Bot
from bot_utils.MusicPlayerInteraction import Player, Track
from bot_utils.MusicPlayerViews import FilterView
from bot_utils.paginator import SimpleEmbedPages, WrapText
from jishaku.functools import executor_function

youtube_url_regex = re.compile(r"https?://(?:www\.)?.+")


@executor_function
def youtube(query, download=False):
    """
    Searches YouTube for a video and returns the results.

    Parameters
    ----------
    query : str
        The query to search YouTube for.
    download : bool
        Whether to download the video.


    Returns
    -------
    dict
        Information about the YouTube video that was queried.

    """
    ytdl = ydl.YoutubeDL(
        {
            "format": "bestaudio/best",
            "restrictfilenames": True,
            "noplaylist": True,
            "nocheckcertificate": True,
            "ignoreerrors": True,
            "logtostderr": False,
            "quiet": True,
            "no_warnings": True,
            "default_search": "auto",
            "source_address": "0.0.0.0",
        }
    )
    info = ytdl.extract_info(query, download=download)
    del ytdl
    return info


class NoChannelProvided(commands.CommandError):
    """
    Error raised when no suitable voice channel was supplied.
    """

    pass


class IncorrectChannelError(commands.CommandError):
    """
    Error raised when commands are issued outside the players' session channel.
    """

    pass


class Music(commands.Cog, wavelink.WavelinkMixin):
    """
    Your friendly music bot
    """

    def __init__(self, bot: Bot):
        self.bot = bot

    async def cog_load(self) -> None:
        # Better way to run code when a cog is loaded.
        """
        Fires when the cog is loaded.

        Returns
        -------
        None
        """
        if not hasattr(self.bot, "wavelink"):
            self.bot.wavelink = wavelink.Client(bot=self.bot)

        self.bot.loop.create_task(self.start_nodes())

    async def start_nodes(self) -> None:
        """
        Connect and initiate nodes.

        Returns
        -------
        None
        """
        await self.bot.wait_until_ready()

        if self.bot.wavelink.nodes:
            previous = self.bot.wavelink.nodes.copy()

            for node in previous.values():
                await node.destroy()

        nodes = {
            "MAIN": {
                "host": "127.0.0.1",
                "port": 2333,
                "rest_uri": "http://127.0.0.1:2333",
                "password": "youshallnotpass",
                "identifier": "MAIN",
                "region": "us_central",
            },
            "Lavalink": {
                "host": "lava.link",
                "port": 80,
                "rest_uri": "http://lava.link:80",
                "password": "",
                "identifier": "Lavalink",
                "region": "us_central",
            },
        }

        for n in nodes.values():
            await self.bot.wavelink.initiate_node(**n)

    @wavelink.WavelinkMixin.listener()
    async def on_node_ready(self, node: wavelink.Node):
        """
        Fires when a node is ready.

        Parameters
        ----------
        node : wavelink.Node
            The node that is ready.

        Returns
        -------
        None
        """
        self.bot.logger.info(f"Node {node.identifier} is running!", __name="Music Bot")

    @wavelink.WavelinkMixin.listener("on_track_stuck")
    @wavelink.WavelinkMixin.listener("on_track_end")
    @wavelink.WavelinkMixin.listener("on_track_exception")
    async def on_player_stop(self, node: wavelink.Node, payload):
        """
        Fires when a player stops.

        Parameters
        ----------
        node : wavelink.Node
            The node that is ready.
        payload : wavelink.Payload
            The payload of the event.

        Returns
        -------
        None
        """
        await payload.player.play_next_song()

    @commands.Cog.listener("on_voice_state_update")
    async def DJ_assign(
        self,
        member: disnake.Member,
        before: disnake.VoiceState,
        after: disnake.VoiceState,
    ):
        """
        Assign DJ role to the user who is currently playing music.

        Parameters
        ----------
        member : disnake.Member
            The member who is currently playing music.

        before : disnake.VoiceState
            The voice state before the update.

        after : disnake.VoiceState
            The voice state after the update.

        Returns
        -------
        None
        """
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

    async def cog_slash_command_error(
        self, ctx: disnake.ApplicationCommandInteraction, error: Exception
    ) -> None:
        """
        Cog wide error handler.

        Parameters
        ----------
        ctx : disnake.ApplicationCommandInteraction
            The Interaction of the command.

        error : Exception
            The error that was raised.

        Returns
        -------
        None
        """
        if ctx.response.is_done():
            safe_send = ctx.followup.send
        else:
            safe_send = ctx.response.send_message
        if isinstance(error, IncorrectChannelError):
            return

        if isinstance(error, NoChannelProvided):
            return await safe_send(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['redtick']} `You must be connected to a voice channel.`",
                    colour=disnake.Colour.random(),
                )
            )

        # ignore all other exception types, but print them to stderr
        else:
            error_msg = "".join(
                traceback.format_exception(type(error), error, error.__traceback__)
            )
            await safe_send(
                embed=disnake.Embed(
                    description=f"**Error invoked by: {str(ctx.author)}**\nCommand: {ctx.application_command.name}\nError: "
                    f"```py\n{error_msg}```",
                    color=disnake.Colour.random(),
                )
            )

            print(
                f"Ignoring exception in command {ctx.application_command}: ",
                file=sys.stderr,
            )
            traceback.print_exception(
                type(error), error, error.__traceback__, file=sys.stderr
            )

    async def cog_before_slash_command_invoke(
        self, ctx: disnake.ApplicationCommandInteraction
    ) -> None:
        """
        Checks if the slash command is invoked in the correct channel and the user has joined in the correct channel.

        Parameters
        ----------
        ctx : disnake.ApplicationCommandInteraction
            The Interaction of the command.

        Returns
        -------
        None
        """
        if ctx.response.is_done():
            safe_send = ctx.followup.send
        else:
            safe_send = ctx.response.send_message

        music_player: Player = self.bot.wavelink.get_player(
            ctx.guild.id, cls=Player, context=ctx
        )

        if music_player.context:
            if music_player.context.channel != ctx.channel:
                await ctx.response.send_message(
                    f"{ctx.author.mention}, you must be in {music_player.context.channel.mention} for this session."
                )
                raise IncorrectChannelError
        else:
            pass

        if ctx.application_command.name == "play" and not music_player.context:
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
                await safe_send(
                    embed=disnake.Embed(
                        description=f"{self.bot.icons['info']} You must be in `{channel.name}` to use voice commands.",
                        colour=disnake.Colour.random(),
                    )
                )
                raise IncorrectChannelError

    def vote_check(self, ctx: disnake.ApplicationCommandInteraction):
        """
        Returns required votes based on amount of members in a channel.

        Parameters
        ----------
        ctx : disnake.ApplicationCommandInteraction
            The Interaction of the command.

        Returns
        -------
        int
            The required votes.
        """
        player: Player = self.bot.wavelink.get_player(
            guild_id=ctx.guild.id, cls=Player, context=ctx
        )
        channel = self.bot.get_channel(int(player.channel_id))
        required = math.ceil((len(channel.members) - 1) / 2.5)

        if ctx.application_command.name == "stop":
            if len(channel.members) == 3:
                required = 2

        return required

    def is_author(self, ctx: disnake.ApplicationCommandInteraction):
        """
        Check whether the user is the command invoker / ctx.author`.

        Parameters
        ----------
        ctx : disnake.ApplicationCommandInteraction
            The Interaction of the command.

        Returns
        -------
        bool
            Whether the user is the command invoker / ctx.author or do they have permissions to kick members.`.
        """
        player: Player = self.bot.wavelink.get_player(
            guild_id=ctx.guild.id, cls=Player, context=ctx
        )

        return (
            player.dj == ctx.author or ctx.author.guild_permissions.kick_members
        )  # you can change your
        # permissions here.

    async def connect(
        self,
        ctx: disnake.ApplicationCommandInteraction,
        channel: typing.Union[disnake.VoiceChannel, disnake.StageChannel] = None,
    ) -> None:
        """
        Connect to a voice channel.

        Parameters
        ----------
        ctx : disnake.ApplicationCommandInteraction
            The Interaction of the command.

        channel : disnake.VoiceChannel, Optional
            The voice channel to connect to.

        Returns
        -------
        None
        """

        music_player: Player = self.bot.wavelink.get_player(
            guild_id=ctx.guild.id, cls=Player, context=ctx
        )

        if music_player.is_connected:
            return

        channel = getattr(ctx.author.voice, "channel", channel)
        if channel is None:
            raise NoChannelProvided

        await music_player.connect(channel.id)
        await ctx.channel.send(
            embed=disnake.Embed(
                title=f":zzz: Joined in {channel}", color=disnake.Colour.random()
            ).set_footer(text=f"Requested by {ctx.author.name}")
        )

    @commands.slash_command()
    async def youtube(self, ctx: disnake.ApplicationCommandInteraction):
        pass

    @youtube.sub_command(description="Search youtube videos")
    async def video(
        self,
        ctx: disnake.ApplicationCommandInteraction,
        query: str = Param(description="Video to search for."),
    ):
        """
        A command that searches YouTube videos.

        Parameters
        ----------
        ctx : disnake.ApplicationCommandInteraction
            The Interaction of the command.

        query : str
            The query to search for.

        Examples
        --------
        `/youtube video query: dank memes`
        """
        await ctx.response.send_message("Searching...")
        if re.search(r"^(https?\:\/\/)?((www\.)?youtube\.com|youtu\.?be)\/.+$", query):
            async with ctx.channel.typing():
                query = (await youtube(query))["title"]

        async with ctx.channel.typing():
            videos = (await (VideosSearch(query, limit=15)).next())["result"]

        if len(videos) == 0:
            return await ctx.response.send_message(
                "I could not find a video with that query"
            )

        embeds = []

        for video in videos:
            url = "https://www.youtube.com/watch?v=" + video["id"]
            channel_url = "https://www.youtube.com/channel/" + video["channel"]["id"]
            em = disnake.Embed(
                title=video["title"], url=url, color=disnake.Colour.random()
            )
            em.add_field(
                name="Channel",
                value=f"[{video['channel']['name']}]({channel_url})",
                inline=True,
            )
            em.add_field(
                name="Duration", value=humanize.intword(video["duration"]), inline=True
            )
            em.add_field(
                name="Views", value=humanize.intword(video["viewCount"]["text"])
            )
            em.set_footer(
                text=f"Use the buttons for navigating • Page: {int(videos.index(video)) + 1}/{len(videos)}"
            )
            em.set_thumbnail(url=video["thumbnails"][0]["url"])
            embeds.append(em)

        pag = SimpleEmbedPages(entries=embeds, ctx=ctx)
        await pag.start()

    @youtube.sub_command(description="Search youtube channels")
    async def channel(
        self,
        ctx: disnake.ApplicationCommandInteraction,
        query: str = Param(description="Channel Query"),
    ):
        """
        A command that searches YouTube channels.

        Parameters
        ----------
        ctx : disnake.ApplicationCommandInteraction
            The Interaction of the command.

        query : str
            The query to search for.

        Examples
        --------
        `/youtube channel query: one vilage`
        """

        async with ctx.channel.typing():
            channels = (await (ChannelsSearch(query, limit=15, region="US")).next())[
                "result"
            ]

        if len(channels) == 0:
            return await ctx.response.send_message(
                embed=disnake.Embed(
                    title="Channel",
                    description="I could not find a channel with that query.",
                    color=disnake.Colour.random(),
                )
            )

        await ctx.response.send_message("Searching...")
        embeds = []

        for channel in channels:
            url = "https://www.youtube.com/channel/" + channel["id"]
            if not channel["thumbnails"][0]["url"].startswith("https:"):
                thumbnail = f"https:{channel['thumbnails'][0]['url']}"
            else:
                thumbnail = channel["thumbnails"][0]["url"]
            if channel["descriptionSnippet"] is not None:
                em = disnake.Embed(
                    title=channel["title"],
                    description=" ".join(
                        text["text"] for text in channel["descriptionSnippet"]
                    ),
                    url=url,
                    color=disnake.Colour.random(),
                )
            else:
                em = disnake.Embed(
                    title=channel["title"], url=url, color=disnake.Colour.random()
                )
            em.add_field(
                name="Videos",
                value="".join(
                    channel["videoCount"] if channel["videoCount"] is not None else "0"
                ),
                inline=True,
            )
            em.add_field(
                name="Subscribers",
                value="".join(
                    channel["subscribers"]
                    if channel["subscribers"] is not None
                    else "0"
                ),
                inline=True,
            )
            em.set_thumbnail(url=thumbnail)
            embeds.append(em)

        pag = SimpleEmbedPages(entries=embeds, ctx=ctx)
        await pag.start()

    @commands.slash_command(description="Play or queue a song with the given query.")
    async def play(
        self,
        ctx: disnake.ApplicationCommandInteraction,
        query: str = Param(description="Song search"),
    ):
        """
        A command that will play your favorite song and if a song is already playing, it will add the song in
        queue.

        Parameters
        ----------
        ctx: disnake.ApplicationCommandInteraction
            The Interaction of the command.

        query: str
            The query to search for.

        Examples
        --------
        `/play query: "50 cent - love me"`
        """
        player: Player = self.bot.wavelink.get_player(
            guild_id=ctx.guild.id, cls=Player, context=ctx
        )
        await ctx.response.defer()

        if not player.is_connected:
            await self.connect(ctx=ctx)

        query = query.strip("<>")
        if not youtube_url_regex.match(query):
            query = f"ytsearch:{query}"

        tracks = await self.bot.wavelink.get_tracks(query)
        if not tracks:
            return await ctx.edit_original_message(
                content=f"{self.bot.icons['redtick']} No songs were found with that query. "
                f"Please try again.",
            )

        if isinstance(tracks, wavelink.TrackPlaylist):
            for track in tracks.tracks:
                track = Track(track.id, track.info, requester=ctx.author)
                await player.queue.put(track)

            await ctx.channel.send(
                f'```ini\nAdded the playlist {tracks.data["playlistInfo"]["name"]}'
                f" with {len(tracks.tracks)} songs to the queue.\n```",
            )
        else:
            track = Track(tracks[0].id, tracks[0].info, requester=ctx.author)
            await ctx.edit_original_message(
                content=f"\n{self.bot.icons['headphones']} Enqueued `{track.title}` to the Queue\n"
            )
            await player.queue.put(track)

        if not player.is_playing:
            await player.play_next_song()

    @commands.slash_command(
        description="Switch the channel where the bot was first invoked."
    )
    async def switch_channel(
        self,
        ctx: disnake.ApplicationCommandInteraction,
        channel: disnake.TextChannel = Param(description="Your channel"),
    ):
        """
        A command that will switch to a different channel and set it as the channel where the bot was invoked.

        This command is useful when you want to play music in a different channel than the one where the bot was
        invoked before.

        Parameters
        ----------
        ctx : disnake.ApplicationCommandInteraction
            The Interaction of the command.

        channel : disnake.TextChannel
            The channel where the bot will be invoked.

        Examples
        --------
        `/switch_channel channel: #general`
        """
        player: Player = self.bot.wavelink.get_player(
            guild_id=ctx.guild.id, cls=Player, context=ctx
        )
        if not player.is_connected:
            return await ctx.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['redtick']} `You must be connected to a voice channel.`",
                    colour=disnake.Colour.random(),
                ),
                delete_after=10,
            )
        if not self.is_author(ctx):
            await ctx.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['info']} Only `{player.dj} can switch channels.`",
                    color=disnake.Colour.random(),
                ),
                delete_after=10,
            )

        player.channel_id = channel.id
        await ctx.response.send_message(
            embed=disnake.Embed(
                description=f"{self.bot.icons['greentick']} `Switched to {channel.name}`",
                colour=disnake.Colour.random(),
            ),
            delete_after=10,
        )

    @commands.slash_command(description="Pause the currently playing song.")
    async def pause(self, ctx: disnake.ApplicationCommandInteraction):
        """
        A command that will pause the music player, if it is playing a track.

        Parameters
        ----------
        ctx: disnake.ApplicationCommandInteraction
            The Interaction of the command.

        Examples
        --------
        `/pause`
        """
        player: Player = self.bot.wavelink.get_player(
            guild_id=ctx.guild.id, cls=Player, context=ctx
        )

        if not player.is_connected:
            return await ctx.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['redtick']} `You must be connected to a voice channel.`",
                    colour=disnake.Colour.random(),
                ),
                delete_after=10,
            )

        if not player.is_playing:
            return await ctx.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['redtick']} `There is no track playing right now.`",
                    colour=disnake.Colour.random(),
                )
            )

        if player.is_paused:
            return await ctx.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['redtick']} `The player is already paused.`",
                    colour=disnake.Colour.random(),
                ),
                delete_after=10,
            )

        if self.is_author(ctx):
            await ctx.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['info']} `{player.dj} has paused the player.",
                    color=disnake.Colour.random(),
                ),
                delete_after=10,
            )
            player.pause_votes.clear()

            return await player.set_pause(True)

        required = self.vote_check(ctx)
        player.pause_votes.add(ctx.author)

        if len(player.pause_votes) >= required:
            await ctx.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['greentick']} Vote to pause passed. Pausing player.",
                    color=disnake.Colour.random(),
                ),
                delete_after=10,
            )
            player.pause_votes.clear()
            await player.set_pause(True)
        else:
            await ctx.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['info']} {ctx.author} has voted to pause the player.",
                    color=disnake.Colour.random(),
                ),
            )

    @commands.slash_command(description="Resumes a currently paused song.")
    async def resume(self, ctx: disnake.ApplicationCommandInteraction):
        """
        A command that will resume the music player if it is paused.

        Parameters
        ----------
        ctx : disnake.ApplicationCommandInteraction
            The Interaction of the command.

        Examples
        --------
        `/resume`
        """
        player: Player = self.bot.wavelink.get_player(
            guild_id=ctx.guild.id, cls=Player, context=ctx
        )

        if not player.is_connected:
            return await ctx.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['redtick']} `You must be connected to a voice channel.`",
                    colour=disnake.Colour.random(),
                ),
                delete_after=10,
            )

        if not player.is_playing:
            return await ctx.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['redtick']} `There is no track playing right now.`",
                    colour=disnake.Colour.random(),
                )
            )

        if not player.is_paused:
            return await ctx.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['redtick']} `The player is not paused.`",
                    colour=disnake.Colour.random(),
                ),
                delete_after=10,
            )

        if self.is_author(ctx):
            await ctx.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['info']} `{player.dj}` has resumed the player.",
                    color=disnake.Colour.random(),
                ),
                delete_after=10,
            )
            player.resume_votes.clear()

            return await player.set_pause(False)

        required = self.vote_check(ctx)
        player.resume_votes.add(ctx.author)

        if len(player.resume_votes) >= required:
            await ctx.response.send_message(
                "Vote to resume passed. Resuming player.", delete_after=10
            )
            player.resume_votes.clear()
            await player.set_pause(False)
        else:
            await ctx.response.send_message(
                f"{ctx.author} has voted to resume the song.",
            )

    @commands.slash_command(description="Skip the currently playing song.")
    async def skip(self, ctx: disnake.ApplicationCommandInteraction):
        """
        A command that will skip to the next song in queue. You need to have songs in queue to skip.
        The DJ of the song, can skip it without voting, else the members listening to the track, need to vote to skip.

        Parameters
        ----------
        ctx: disnake.ApplicationCommandInteraction
            The Interaction of the command.

        Examples
        --------
        `/skip`
        """
        player: Player = self.bot.wavelink.get_player(
            guild_id=ctx.guild.id, cls=Player, context=ctx
        )

        if not player.is_connected:
            return await ctx.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['redtick']} `You must be connected to a voice channel.`",
                    colour=disnake.Colour.random(),
                ),
                delete_after=10,
            )

        if self.is_author(ctx):
            await ctx.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['info']} `{player.dj}` has skipped the song.",
                    color=disnake.Colour.random(),
                ),
                delete_after=10,
            )
            player.skip_votes.clear()

            return await player.stop()

        required = self.vote_check(ctx)
        player.skip_votes.add(ctx.author)

        if len(player.skip_votes) >= required:
            await ctx.response.send_message(
                "Vote to skip passed. Skipping song.", delete_after=10
            )
            player.skip_votes.clear()
            await player.stop()
        else:
            await ctx.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['info']} `{ctx.author}` has voted to skip the song.",
                    color=disnake.Colour.random(),
                ),
            )

    @commands.slash_command(
        description="Stop the currently playing song and the music player."
    )
    async def stop(self, ctx: disnake.ApplicationCommandInteraction):
        """
        A command that will stop the currently playing song and the music player and only the DJ can use this command.

        Parameters
        ----------
        ctx: disnake.ApplicationCommandInteraction
            The Interaction of the command.

        Examples
        --------
        `/stop`
        """
        player: Player = self.bot.wavelink.get_player(
            guild_id=ctx.guild.id, cls=Player, context=ctx
        )

        if not player.is_connected:
            return await ctx.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['redtick']} `You must be connected to a voice channel.`",
                    colour=disnake.Colour.random(),
                ),
                delete_after=10,
            )

        if not player.is_playing:
            return await ctx.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['redtick']} `There is no track playing right now.`",
                    colour=disnake.Colour.random(),
                )
            )

        if self.is_author(ctx):
            await ctx.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['info']} `{player.dj}` has stopped the player.",
                    color=disnake.Colour.random(),
                ),
                delete_after=10,
            )
            return await player.teardown()

        required = self.vote_check(ctx)
        player.stop_votes.add(ctx.author)

        if len(player.stop_votes) >= required:
            await ctx.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['info']} Vote passed, stopping the player.",
                    color=disnake.Colour.random(),
                )
            )
            await player.teardown()
        else:
            await ctx.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['info']} `{ctx.author}` has voted to stop the song.",
                    color=disnake.Colour.random(),
                )
            )

    @commands.slash_command(description="Disconnect the bot and stop the music player.")
    async def disconnect(self, ctx: disnake.ApplicationCommandInteraction):
        """
        A command that will stop and clear the music player and disconnect the bot.

        Parameters
        ----------
        ctx: disnake.ApplicationCommandInteraction
            The Interaction of the command.

        Examples
        --------
        `/disconnect`
        """
        player: Player = self.bot.wavelink.get_player(
            guild_id=ctx.guild.id, cls=Player, context=ctx
        )

        if not player.is_connected:
            return await ctx.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['redtick']} `You must be connected to a voice channel.`",
                    colour=disnake.Colour.random(),
                ),
                delete_after=10,
            )

        if not self.is_author(ctx):
            return await ctx.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['info']} Only `{player.dj}` can disconnect the player.",
                    color=disnake.Colour.random(),
                ),
                delete_after=10,
            )
        await ctx.response.send_message(
            embed=disnake.Embed(
                description=f"{self.bot.icons['info']} `{player.dj}` has disconnected the player.",
                color=disnake.Colour.random(),
            )
        )
        await player.teardown()

    @commands.slash_command(description="Change the players volume, between 1 and 100.")
    async def volume(
        self,
        ctx: disnake.ApplicationCommandInteraction,
        vol: int = Param(description="The volume to set the player to.", gt=1, lt=100),
    ):
        """
        A command that will alter the volume of the music player, between 1 and 100.

        Parameters
        ----------
        ctx: disnake.ApplicationCommandInteraction
            The Interaction of the command.

        vol: int
            The volume to set the player to.

        Examples
        --------
        `/volume vol: 50`
        """
        player: Player = self.bot.wavelink.get_player(
            guild_id=ctx.guild.id, cls=Player, context=ctx
        )

        if not player.is_connected:
            return await ctx.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['redtick']} `You must be connected to a voice channel.`",
                    colour=disnake.Colour.random(),
                )
            )

        if not player.is_playing:
            return await ctx.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['redtick']} `There is no track playing right now.`",
                    colour=disnake.Colour.random(),
                )
            )

        if not self.is_author(ctx):
            return await ctx.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['info']} Only the `{player.dj}` can change the volume of this song.",
                    color=disnake.Colour.random(),
                )
            )

        if not 0 < vol < 101:
            return await ctx.response.send(
                f"{self.bot.icons['info']} Please enter a value between 1 and 100."
            )

        await player.set_volume(vol)
        await ctx.response.send_message(
            embed=disnake.Embed(
                description=f"{self.bot.icons['redtick']} Set the volume "
                f"to **{vol}**%",
                colour=disnake.Colour.random(),
            )
        )

    @commands.slash_command(description="Loops the current playing track.")
    async def loop(self, ctx: disnake.ApplicationCommandInteraction):
        """
        A command that will loop your specific music track and keep playing it repeatedly.
        Use the loop command again to unloop your music track.

        Parameters
        ----------
        ctx: disnake.ApplicationCommandInteraction
            The Interaction of the command.

        Examples
        --------
        `/loop` - Loops the current track.

        `/loop` - unloops the current track.
        """
        player: Player = self.bot.wavelink.get_player(
            guild_id=ctx.guild.id, cls=Player, context=ctx
        )

        if not player.is_connected:
            return await ctx.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['redtick']} `You must be connected to a voice channel.`",
                    colour=disnake.Colour.random(),
                ),
                delete_after=10,
            )

        if not player.is_playing:
            return await ctx.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['redtick']} `There is no track playing right now.`",
                    colour=disnake.Colour.random(),
                )
            )

        if not self.is_author(ctx):
            return await ctx.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['info']} Only the `{player.dj}` can loop this song.",
                    color=disnake.Colour.random(),
                )
            )

        if player.loop is False:
            await ctx.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['greentick']} Looped the current track.",
                    color=disnake.Colour.random(),
                )
            )
            player.loop = True
            return
        if player.loop is True:
            await ctx.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['greentick']} Un-looped the current track.",
                    color=disnake.Colour.random(),
                )
            )
            player.loop = False
            return

    @commands.slash_command(description="Shuffle the players queue.")
    async def shuffle(self, ctx: disnake.ApplicationCommandInteraction):
        """
        A command that will shuffle the entire queue of the current music player instance.
        You need at least 3 songs or more in queue in order to shuffle properly.

         Parameters
        ----------
        ctx: disnake.ApplicationCommandInteraction
            The Interaction of the command.

        Examples
        --------
        `/shuffle`
        """
        player: Player = self.bot.wavelink.get_player(
            guild_id=ctx.guild.id, cls=Player, context=ctx
        )

        if not player.is_connected:
            return await ctx.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['redtick']} `You must be connected to a voice channel.`",
                    colour=disnake.Colour.random(),
                ),
                delete_after=10,
            )

        if player.queue.qsize() < 3:
            return await ctx.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['info']} Add more songs before shuffling.",
                    color=disnake.Colour.random(),
                )
            )

        if self.is_author(ctx):
            await ctx.channel.send(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['info']} `{player.dj}` has shuffled the queue.",
                    color=disnake.Colour.random(),
                )
            )

            player.shuffle_votes.clear()
            return player.queue.shuffle()

        required = self.vote_check(ctx)
        player.shuffle_votes.add(ctx.author)

        if len(player.shuffle_votes) >= required:
            await ctx.channel.send(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['info']} Vote passed, shuffling songs.",
                    color=disnake.Colour.random(),
                )
            )

            player.shuffle_votes.clear()
            player.queue.shuffle()
        else:
            return await ctx.channel.send(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['info']} `{ctx.author}` has voted to shuffle the queue.",
                    color=disnake.Colour.random(),
                )
            )

    @commands.slash_command(description="Clears the entire queue.")
    async def clearqueue(self, ctx: disnake.ApplicationCommandInteraction):
        """
        A command that will clear the entire queue of the current music player instance.

        Parameters
        ----------
        ctx : disnake.ApplicationCommandInteraction
            The Interaction of the command.

        Examples
        --------
        `/clearqueue`
        """
        player: Player = self.bot.wavelink.get_player(
            guild_id=ctx.guild.id, cls=Player, context=ctx
        )

        if not player.is_connected:
            return await ctx.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['redtick']} `You must be connected to a voice channel.`",
                    colour=disnake.Colour.random(),
                ),
                delete_after=10,
            )

        if player.queue.qsize() == 0:
            return await ctx.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['info']} Queue is empty.",
                    color=disnake.Colour.random(),
                )
            )

        if self.is_author(ctx):
            await ctx.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['info']} `{player.dj}` has cleared the queue.",
                    color=disnake.Colour.random(),
                )
            )

            player.clear_votes.clear()
            player.queue.clear()

        required = self.vote_check(ctx)
        player.clear_votes.add(ctx.author)

        if len(player.shuffle_votes) >= required:
            await ctx.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['info']} Vote passed, clearing the queue.",
                    color=disnake.Colour.random(),
                )
            )

            player.clear_votes.clear()
            player.queue.clear()
        else:
            return await ctx.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['info']} `{ctx.author}` has voted to clear the queue.",
                    color=disnake.Colour.random(),
                )
            )

    @commands.slash_command(description="Show lyrics of the current playing song.")
    async def lyrics(
        self,
        ctx: disnake.ApplicationCommandInteraction,
        *,
        name: str = Param(
            description="The name of the song to search  the lyrics of.",
            default=None,
        ),
    ):
        """
        A command that will show the lyrics of the current playing song or the name of the song you want lyrics
        for, if you explicitly specify it.

        Parameters
        ----------
        ctx : disnake.ApplicationCommandInteraction
            The Interaction of the command.

        name : typing.Optional[str]
            The name of the song to search the lyrics of.

        Examples
        --------
        `/lyrics`

        `/lyrics name: "The Chainsmokers - Closer"`
        """
        player: Player = self.bot.wavelink.get_player(
            guild_id=ctx.guild.id, cls=Player, context=ctx
        )
        if name is None:
            name = player.now.title

        if not player.is_connected:
            return await ctx.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['redtick']} `You must be connected to a voice channel.`",
                    colour=disnake.Colour.random(),
                )
            )

        resp = await self.bot.session.get(
            f"https://some-random-api.ml/lyrics?title={name}"
        )

        if not 200 <= resp.status <= 299:
            return await ctx.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['redtick']} `Lyrics for this song is not found.`",
                    colour=disnake.Colour.random(),
                ),
                delete_after=10,
            )

        if not player.is_playing:
            return await ctx.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['redtick']} `There is no track playing right now.`",
                    colour=disnake.Colour.random(),
                )
            )

        data = await resp.json()

        lyrics = data["lyrics"]
        content = WrapText(lyrics, length=1000)
        await ctx.response.send_message(content="Generating lyrics....")

        embeds = []
        for text in content:
            embed = disnake.Embed(
                title=data["title"],
                description=text,
                colour=ctx.author.colour,
                timestamp=disnake.utils.utcnow(),
            )
            embed.set_thumbnail(url=data["thumbnail"]["genius"])
            embed.set_author(name=data["author"])

            embeds.append(embed)
        pag = SimpleEmbedPages(entries=embeds, ctx=ctx)
        await pag.start()

    @commands.slash_command(description="Add a Filter to the player.")
    async def filter(self, ctx: disnake.ApplicationCommandInteraction):
        """
        A command that can add Filter to the music player of your choice.
        You will be asked to select between filters.
        There are four inbuilt filters:

        Tremolo -> A piano-like filter.
        Vibrato -> A vibrato filter.
        8D -> An 8D audio filter.
        Vibrato -> A vibrato filter.


        Parameters
        ----------
        ctx : disnake.ApplicationCommandInteraction
            The Interaction of the command.


        Examples
        --------
        `/filter`
        """

        player: Player = self.bot.wavelink.get_player(
            guild_id=ctx.guild.id, cls=Player, context=ctx
        )

        if not player.is_connected:
            return await ctx.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['redtick']} `You must be connected to a voice channel.`",
                    colour=disnake.Colour.random(),
                )
            )

        if not self.is_author(ctx):
            return await ctx.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['info']} Only the `{player.dj}` can add filters to the player.",
                    color=disnake.Colour.random(),
                )
            )

        if not player.is_playing:
            return await ctx.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['redtick']} `There is no track playing right now.`",
                    colour=disnake.Colour.random(),
                )
            )

        await ctx.response.send_message(
            content="Select a Filter:",
            view=FilterView(interaction=ctx, player=player),
        )

    @commands.slash_command(description="Create and set a custom filter.")
    async def create_filter(self, ctx: disnake.ApplicationCommandInteraction):
        pass

    @create_filter.sub_command(description="Create a Tremolo Filter.")
    async def channel_mix(
        self,
        ctx: disnake.ApplicationCommandInteraction,
        left_to_right: float = Param(description="Left to Right", default=0.5),
        right_to_left: float = Param(description="Right to Left", default=0.5),
        right_to_right: float = Param(description="Right to Right", default=0.5),
        left_to_left: float = Param(description="Left to Left", default=0.5),
    ):

        """
        Filter which manually adjusts the panning of the audio, which can make
        for some cool effects when done correctly.
        Remember, this can adversely affect the audio quality.

        Parameters
        ----------
        ctx : disnake.ApplicationCommandInteraction
            The Interaction of the command.

        left_to_right : float
            The left to right panning.

        right_to_left : float
            The right to left panning.

        right_to_right : float
            The right to right panning.

        left_to_left : float
            The left to left panning.

        Examples
        --------
        `/create_filter channel_mix left_to_right=0.5 right_to_left=0.5 right_to_right=0.5 left_to_left=0.5`
        """

        player: Player = self.bot.wavelink.get_player(
            guild_id=ctx.guild.id, cls=Player, context=ctx
        )

        if not player.is_connected:
            return await ctx.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['redtick']} `You must be connected to a voice channel.`",
                    colour=disnake.Colour.random(),
                ),
                delete_after=10,
            )

        if not player.is_playing:
            return await ctx.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['redtick']} `There is no track playing right now.`",
                    colour=disnake.Colour.random(),
                )
            )

        if not self.is_author(ctx):
            return await ctx.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['info']} Only the `{player.dj}` can set the filter to the player.",
                    color=disnake.Colour.random(),
                )
            )

        filter_ = wavelink.BaseFilter.build_from_channel_mix(
            left_to_left=left_to_left,
            left_to_right=left_to_right,
            right_to_left=right_to_left,
            right_to_right=right_to_right,
        )

        await player.set_filter(filter_)
        await ctx.response.send_message(
            embed=disnake.Embed(
                description=f"{self.bot.icons['greentick']} `Filter set to:` {filter_.name}",
                colour=disnake.Colour.random(),
            )
        )

    @create_filter.sub_command(
        description="Build a custom Filter from base TimeScale Filter."
    )
    async def time_scale(
        self,
        ctx: disnake.ApplicationCommandInteraction,
        speed: float = Param(description="Speed", default=1.0),
        pitch: float = Param(description="Pitch", default=1.0),
        rate: float = Param(description="Rate", default=1.0),
    ):
        """
        Filter which changes the speed and pitch of a track.
        You can make some very nice effects with this filter.

         Parameters
         ----------
         ctx : disnake.ApplicationCommandInteraction
             The Interaction of the command.

         speed : float
             The speed.

         pitch : float
             The pitch.

         rate : float
             The rate.

        Examples
        --------
        `/create_filter time_scale time_scale speed=1.5 pitch=1.5 rate=1.5`
        """

        player: Player = self.bot.wavelink.get_player(
            guild_id=ctx.guild.id, cls=Player, context=ctx
        )

        if not player.is_connected:
            return await ctx.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['redtick']} `You must be connected to a voice channel.`",
                    colour=disnake.Colour.random(),
                ),
                delete_after=10,
            )

        if not player.is_playing:
            return await ctx.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['redtick']} `There is no track playing right now.`",
                    colour=disnake.Colour.random(),
                )
            )

        if not self.is_author(ctx):
            return await ctx.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['info']} Only the `{player.dj}` can set the filter to the player.",
                    color=disnake.Colour.random(),
                )
            )

        filter_ = wavelink.BaseFilter.build_from_timescale(
            speed=speed, pitch=pitch, rate=rate
        )

        await player.set_filter(filter_)
        await ctx.response.send_message(
            embed=disnake.Embed(
                description=f"{self.bot.icons['greentick']} `Filter set to:` {filter_.name}",
                colour=disnake.Colour.random(),
            )
        )

    @create_filter.sub_command(
        description="Build a custom Filter from base Distortion Filter."
    )
    async def distortion(
        self,
        ctx: disnake.ApplicationCommandInteraction,
        sin_offset: float = Param(description="Sin Offset", default=0.0),
        cos_offset: float = Param(description="Cos Offset", default=0.0),
        sin_scale: float = Param(description="Sin Scale", default=1.0),
        cos_scale: float = Param(description="Cos Scale", default=1.0),
        tan_offset: float = Param(description="Tan Offset", default=0.0),
        tan_scale: float = Param(description="Tan Scale", default=1.0),
        offset: float = Param(description="Offset", default=0.0),
        scale: float = Param(description="Scale", default=1.0),
    ):
        """
        This slash command builds a custom Filter from base Distortion Filter. This filter can be used to distort the
        audio. Very useful for making some nice effects, if used correctly.

        Parameters
        ----------
        ctx : disnake.ApplicationCommandInteraction
             The Interaction of the command.

        sin_offset : float
            The sin offset.

        sin_scale : float
            The sin scale.

        cos_offset : float
            The cos offset.

        cos_scale : float
            The cos scale.

        tan_offset : float
            The tan offset.

        tan_scale : float
            The tan scale.

        offset : float
            The offset.

        scale : float
            The scale.

        Examples
        --------
        `/create_filter distortion sin_offset=0.5 sin_scale=1.5 cos_offset=0.5 cos_scale=1.5
        tan_offset=0.5 tan_scale=1.5 offset=0.5 scale=1.5`
        """

        player: Player = self.bot.wavelink.get_player(
            guild_id=ctx.guild.id, cls=Player, context=ctx
        )

        if not player.is_connected:
            return await ctx.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['redtick']} `You must be connected to a voice channel.`",
                    colour=disnake.Colour.random(),
                ),
                delete_after=10,
            )

        if not player.is_playing:
            return await ctx.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['redtick']} `There is no track playing right now.`",
                    colour=disnake.Colour.random(),
                )
            )

        if not self.is_author(ctx):
            return await ctx.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['info']} Only the `{player.dj}` can set the filter to the player.",
                    color=disnake.Colour.random(),
                )
            )

        filter_ = wavelink.BaseFilter.build_from_distortion(
            sin_offset=sin_offset,
            cos_offset=cos_offset,
            sin_scale=sin_scale,
            cos_scale=cos_scale,
            tan_offset=tan_offset,
            tan_scale=tan_scale,
            offset=offset,
            scale=scale,
        )

        await player.set_filter(filter_)
        await ctx.response.send_message(
            embed=disnake.Embed(
                description=f"{self.bot.icons['greentick']} `Filter set to:` {filter_.name}",
                colour=disnake.Colour.random(),
            )
        )

    @commands.slash_command(description="Display the player's queued songs.")
    async def queue(self, ctx: disnake.ApplicationCommandInteraction):
        """
        A command that will show all the songs that queued in the music player. It has pagination,
        so it's easy for you to browse.

        Parameters
        ----------
        ctx : disnake.ApplicationCommandInteraction
            The Interaction of the command.

        Examples
        --------
         `/queue`
        """
        player: Player = self.bot.wavelink.get_player(
            guild_id=ctx.guild.id, cls=Player, context=ctx
        )

        if not player.is_connected:
            return await ctx.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['redtick']} `You must be connected to a voice channel.`",
                    colour=disnake.Colour.random(),
                ),
                delete_after=10,
            )

        if player.queue.qsize() == 0:
            return await ctx.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['info']} There are no more songs "
                    f"in the queue.",
                    colour=disnake.Colour.random(),
                ),
            )
        await ctx.response.send_message("Loading...")

        entries = []
        for track in player.queue._queue:
            embed = disnake.Embed(
                title=f"`{len(player.queue._queue)}` tracks in queue....",
                color=disnake.Colour.random(),
            )
            embed.add_field(name=f"{track.title}", value=track.uri, inline=False)
            entries.append(embed)

        paginator = SimpleEmbedPages(entries=entries, ctx=ctx)

        await paginator.start()

    @commands.slash_command(description="Show the current playing song")
    async def nowplaying(self, ctx: disnake.ApplicationCommandInteraction):
        """
        A command that will show the information about the track that has been playing.

        Parameters
        ----------
        ctx : disnake.ApplicationCommandInteraction
            The Interaction of the command.

        Examples
        --------
         `/nowplaying`
        """
        player: Player = self.bot.wavelink.get_player(
            guild_id=ctx.guild.id, cls=Player, context=ctx
        )

        if not player.is_connected:
            return await ctx.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['redtick']} `You must be connected to a voice channel.`",
                    colour=disnake.Colour.random(),
                )
            )

        if not player.is_playing:
            return await ctx.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['redtick']} `There is no song playing right now.`",
                    colour=disnake.Colour.random(),
                )
            )

        embed = await player.make_song_embed()  # shows the song embed.
        await ctx.response.send_message(embed=embed)

    @commands.slash_command(description="Save the current playing song in your dms.")
    async def save(self, ctx: disnake.ApplicationCommandInteraction):
        """
        A command that will show the information about the track that has been playing and send it in your dms,
        if possible, so make sure that you have kept your dms open.

        Parameters
        ----------
        ctx : disnake.ApplicationCommandInteraction
            The Interaction of the command.

        Examples
        --------
         `/save`
        """
        player: Player = self.bot.wavelink.get_player(
            guild_id=ctx.guild.id, cls=Player, context=ctx
        )

        if not player.is_connected:
            return await ctx.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['redtick']} `You must be connected to a voice channel.`",
                    colour=disnake.Colour.random(),
                )
            )

        if not player.is_playing:
            return await ctx.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['redtick']} `There is no song playing right now.`",
                    colour=disnake.Colour.random(),
                )
            )

        embed = await player.make_song_embed()  # shows the song embed.
        await ctx.response.send_message(content="Check your dms.", ephemeral=True)
        await ctx.author.send(embed=embed)

    @commands.slash_command(description="Seek to a specific time in the song.")
    async def seek(
        self,
        ctx: disnake.ApplicationCommandInteraction,
        position: str = Param(
            description="The time position to seek to. For eg: /seek 3:56"
        ),
    ):
        """
        A command that will seek aka skip to a specific part of a track in a song that has been playing.

        Parameters
        ----------
        ctx : disnake.ApplicationCommandInteraction
            The Interaction of the command.

        position : str
            The time position to seek to. For eg: /seek 3:56

        Examples
        --------
        `/seek position: 3:56` -> This will skip to 3 minutes and 56 seconds in the playing track.
        """
        player: Player = self.bot.wavelink.get_player(
            guild_id=ctx.guild.id, cls=Player, context=ctx
        )
        time_regex = r"([0-9]{1,2})[:ms](([0-9]{1,2})s?)?"

        if not player.is_connected:
            return await ctx.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['redtick']} `You must be connected to a voice channel.`",
                    colour=disnake.Colour.random(),
                )
            )

        if not player.is_playing:
            return await ctx.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['redtick']} `There is no song playing right now.`",
                    colour=disnake.Colour.random(),
                )
            )
        if player.is_paused:
            return await ctx.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['redtick']} `There player is paused right now, resume it in order to "
                    f"seek.`",
                    colour=disnake.Colour.random(),
                )
            )

        if not (match := re.match(time_regex, position)):
            await ctx.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['greentick']} `{position} is not a valid time format.`"
                )
            )
        if match.group(3):
            secs = (int(match.group(1)) * 60) + (int(match.group(3)))
        else:
            secs = int(match.group(1))

        await player.seek(secs * 1000)
        await ctx.response.send_message(
            embed=disnake.Embed(
                description=f"{self.bot.icons['greentick']} Successfully seeked.",
                colour=disnake.Colour.random(),
            )
        )

    @commands.slash_command(
        description="Swap the current DJ to another member in the voice channel."
    )
    async def swap_dj(
        self,
        ctx: disnake.ApplicationCommandInteraction,
        member: disnake.Member = Param(description="The member to swap to"),
    ):
        """
        A command that will switch the player's DJ to another member in the same voice channel.

        Parameters
        ----------
        ctx : disnake.ApplicationCommandInteraction
            The Interaction of the command.

        member: disnake.Member
            The member to swap to.

        Examples
        --------
        `/swap_dj member: @KortaPo`
        """
        player: Player = self.bot.wavelink.get_player(
            guild_id=ctx.guild.id, cls=Player, context=ctx
        )

        if not player.is_connected:
            return await ctx.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['redtick']} `You must be connected to a voice channel.`",
                    colour=disnake.Colour.random(),
                )
            )

        if not self.is_author(ctx):
            return await ctx.channel.send(
                embed=disnake.Embed(
                    description=f"Only admins and the DJ can use this command.",
                    color=disnake.Colour.random(),
                )
            )

        members = self.bot.get_channel(int(player.channel_id)).members

        if member and member not in members:
            return await ctx.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['info']} `{member}` is not currently in voice, so they cannot be a DJ."
                ),
            )

        if member and member == player.dj:
            return await ctx.response.send_message(
                "Cannot swap DJ to the current DJ... :)",
            )

        if len(members) <= 2:
            return await ctx.channel.send(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['redtick']} `{member}` No more members to swap to."
                ),
                color=disnake.Colour.red(),
            )

        if member:
            player.dj = member
            return await ctx.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['info']} `{member}` is now a DJ."
                ),
            )

        for m in members:
            if m == player.dj or m.bot:
                continue
            else:
                player.dj = m
                return await ctx.response.send_message(
                    embed=disnake.Embed(
                        description=f"{self.bot.icons['info']} `{member}` is now a DJ.",
                        colour=disnake.Colour.random(),
                    )
                )


def setup(bot):
    bot.add_cog(Music(bot))
