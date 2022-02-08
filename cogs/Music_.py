#  -*- coding: utf-8 -*-
import datetime
import math
import re
import sys
import traceback
import typing

import disnake
import humanize
from disnake.ext import commands
from disnake.ext.commands.params import Param

import wavelink
from core.MusicBot import Bot
from utils.exceptions import IncorrectChannelError, NoChannelProvided
from utils.helpers import ErrorView, LyricsPaginator, SearchService
from utils.MusicPlayerInteraction import Player, QueuePages, Track
from utils.paginators import WrapText
from utils.views import FilterView, SongSelectionView
from wavelink.errors import FilterInvalidArgument

url_regex = re.compile(r"https?://(?:www\.)?.+")

youtube_url_regex = re.compile(
    r"https?://(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/)(?P<id>[\w-]{11})(?:&.+)?$")

SOUNDCLOUD_URL_REGEX = re.compile(
    r"^(https?:\/\/)?(www.)?(m\.)?soundcloud\.com\/[\w\-\.]+(\/)+[\w\-\.]+/?$"
)

SPOTIFY_URL_REGEX = re.compile(
    r"https?://open.spotify.com/(?P<type>album|playlist|track)/(?P<id>[a-zA-Z0-9]+)"
)


class Music(commands.Cog, wavelink.WavelinkMixin):
    """
    Your friendly music bot
    """

    def __init__(self, bot: Bot):
        self.bot = bot

    async def cog_load(self) -> None:
        """
        Fires when the cog is loaded.
        """
        # Better way to run code when a cog is loaded.
        if not hasattr(self.bot, "wavelink"):
            self.bot.wavelink = wavelink.Client(bot=self.bot)

        self.bot.loop.create_task(self.start_nodes())

    async def start_nodes(self) -> None:
        """
        This method is used to start the nodes.
        """
        await self.bot.wait_until_ready()

        if self.bot.wavelink.nodes:
            previous = self.bot.wavelink.nodes.copy()

            for node in previous.values():
                await node.destroy()

        nodes = {
            "MAIN": {
                "host": self.bot.config.lavalink_host,
                "port": self.bot.config.lavalink_port,
                "rest_uri": f"http://{self.bot.config.lavalink_host}:{self.bot.config.lavalink_port}",
                "password": self.bot.config.lavalink_password,
                "identifier": "MAIN",
                "region": "us_central",
            }
        }  # pass your nodes here

        for n in nodes.values():
            await self.bot.wavelink.initiate_node(**n)

    @wavelink.WavelinkMixin.listener()
    async def on_node_ready(self, node: wavelink.Node) -> None:
        """
        Fires when a node is ready.

        Parameters
        ----------
        node: wavelink.Node
            The node that is ready.
        """
        self.bot.logger.info(f"Node {node.identifier} is running!", __name="Music Bot")

    @wavelink.WavelinkMixin.listener("on_track_stuck")
    @wavelink.WavelinkMixin.listener("on_track_end")
    @wavelink.WavelinkMixin.listener("on_track_exception")
    async def on_player_stop(self, node: wavelink.Node, payload) -> None:
        """
        Fires when a player stops.

        Parameters
        ----------
        node : wavelink.Node
            The node that is ready.
        payload : typing.Any
            The payload of the event.
        """
        self.bot.logger.info(f"Player stopped! {node}", __name="Music Bot")
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
            The voice state before the update. This is not used.

        after : disnake.VoiceState
            The voice state after the update.
        """
        if member.bot:
            return

        player: Player = self.bot.wavelink.get_player(member.guild.id, cls=Player)

        if not player.channel_id or not player.context:
            player.node.players.pop(member.guild.id)
            return

        channel: disnake.VoiceChannel = await self.bot.fetch_channel(player.channel_id)

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
            self, interaction: disnake.ApplicationCommandInteraction, error: Exception
    ) -> None:
        """
        Cog wide error handler.

        Parameters
        ----------
        interaction : disnake.ApplicationCommandInteraction
            This parameter takes disnake.ApplicationCommandInteraction object, when this slash command is executed which creates an Interaction.

        error : Exception
            The error that was raised.
        """
        if interaction.response.is_done():
            safe_send = interaction.followup.send
        else:
            safe_send = interaction.response.send_message
        if isinstance(error, IncorrectChannelError):
            return

        if isinstance(error, NoChannelProvided):
            return await safe_send(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['redtick']} `You must be connected to a voice channel.`",
                    colour=disnake.Colour.random(),
                )
            )

        if isinstance(error, disnake.Forbidden):
            return await safe_send(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['redtick']} `I do not have permission to do that.`",
                    colour=disnake.Colour.random(),
                )
            )

        if isinstance(error, wavelink.errors.ZeroConnectedNodes):
            return await safe_send(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['redtick']} `There are no nodes connected.`",
                    colour=disnake.Colour.random(),
                )
            )

        # ignore all other exception types, but print them to stderr
        else:
            error_msg = "".join(
                traceback.format_exception(type(error), error, error.__traceback__)
            )
            paste = await self.bot.mystbin_client.post(error_msg, syntax="py")
            url = paste.url
            await safe_send(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['redtick']} An error has occurred while "
                                f"executing {interaction.application_command.name} command. The error has been generated on "
                                f"mystbin. "
                                f"Please report this to `{', '.join([str(owner) for owner in await self.bot.get_owners])}`",
                    colour=disnake.Colour.random(),
                ),
                view=ErrorView(url=url),
            )

            print(
                f"Ignoring exception in command {interaction.application_command}: ",
                file=sys.stderr,
            )
            traceback.print_exception(
                type(error), error, error.__traceback__, file=sys.stderr
            )

    async def cog_before_slash_command_invoke(
            self, interaction: disnake.ApplicationCommandInteraction
    ) -> None:
        """
        Checks if the slash command is invoked in the correct channel and the user has joined in the correct channel.

        Parameters
        ----------
        interaction : disnake.ApplicationCommandInteraction
            This parameter takes disnake.ApplicationCommandInteraction object, when this slash command is executed which creates an Interaction.
        """
        if interaction.response.is_done():
            safe_send = interaction.followup.send
        else:
            safe_send = interaction.response.send_message

        music_player: Player = self.bot.wavelink.get_player(
            interaction.guild.id, cls=Player, context=interaction
        )
        if music_player.context:
            if music_player.context.channel != interaction.channel:
                await interaction.response.send_message(
                    f"{interaction.author.mention}, you must be in {music_player.context.channel.mention} for this "
                    f"session."
                )
                raise IncorrectChannelError
        else:
            pass
        if interaction.application_command.name == "play" and not music_player.context:
            return

        if not music_player.channel_id:
            return

        channel = self.bot.get_channel(int(music_player.channel_id))
        if not channel:
            return

        if music_player.is_connected:
            if interaction.author not in channel.members:
                await safe_send(
                    embed=disnake.Embed(
                        description=f"{self.bot.icons['info']} You must be in `{channel.name}` to use voice commands.",
                        colour=disnake.Colour.random(),
                    )
                )
                raise IncorrectChannelError

    def vote_check(self, interaction: disnake.ApplicationCommandInteraction):
        """
        Returns required votes based on amount of members in a channel.

        Parameters
        ----------
        interaction : disnake.ApplicationCommandInteraction
            This parameter takes disnake.ApplicationCommandInteraction object, when this slash command is executed
            which creates an Interaction.

        Returns
        -------
        int
            The required votes.
        """
        player: Player = self.bot.wavelink.get_player(
            guild_id=interaction.guild.id, cls=Player, context=interaction
        )
        channel = self.bot.get_channel(int(player.channel_id))
        required = math.ceil((len(channel.members) - 1) / 2.5)

        if interaction.application_command.name == "stop":
            if len(channel.members) == 3:
                required = 2

        return required

    def is_author(self, interaction: disnake.ApplicationCommandInteraction):
        """
        Check whether the user is the command invoker / interaction Author`.

        Parameters
        ----------
        interaction : disnake.ApplicationCommandInteraction
            This parameter takes disnake.ApplicationCommandInteraction object, when this slash command is executed
            which creates an Interaction.

        Returns
        -------
        bool
            Whether the user is the command invoker / interaction Author or do they have permissions to kick members.`.
        """
        player: Player = self.bot.wavelink.get_player(
            guild_id=interaction.guild.id, cls=Player, context=interaction
        )

        return (
                player.dj == interaction.author
                or interaction.author.guild_permissions.kick_members
        )  # you can change your
        # permissions here.

    async def connect(
            self,
            interaction: disnake.ApplicationCommandInteraction,
            channel: typing.Union[disnake.VoiceChannel, disnake.StageChannel] = None,
    ) -> None:
        """
        Connect to a voice channel.

        Parameters
        ----------
        interaction : disnake.ApplicationCommandInteraction
            This parameter takes disnake.ApplicationCommandInteraction object, when this slash command is executed
            which creates an Interaction.

        channel : disnake.VoiceChannel, Optional
            The voice channel to connect to.
        """

        music_player: Player = self.bot.wavelink.get_player(
            guild_id=interaction.guild.id, cls=Player, context=interaction
        )

        if music_player.is_connected:
            return

        channel = getattr(interaction.author.voice, "channel", channel)
        if channel is None:
            raise NoChannelProvided

        await music_player.connect(channel.id)
        await interaction.channel.send(
            embed=disnake.Embed(
                title=f":zzz: Joined in {channel}", color=disnake.Colour.random()
            ).set_footer(text=f"Requested by {interaction.author.name}")
        )

    @commands.slash_command(description="Play or queue a song with the given query.")
    async def play(
            self,
            interaction: disnake.ApplicationCommandInteraction,
            query: str = Param(description="Search your song...."),
            service: str = Param(
                description="The service to search on.", default="youtube"
            ),
    ):
        """
        A command that will play your favorite song and if a song is already playing, it will add the song in
        queue. You can search for songs on a specific service. For example, soundcloud, YouTube, etc.
        Supported Services: YouTube, SoundCloud, Bandcamp, Spotify and more. You can find a list of supported
        by running /help info.
        However, only spotify, souncloud track urls are supported, you cannot search for a song by its name.

        Parameters 
        ---------- 
        interaction: disnake.ApplicationCommandInteraction 
            This parameter takes 
            disnake.ApplicationCommandInteraction object, when this slash command is executed which creates an
            Interaction.

        query: str
            The song query to search for.

        service: str
            The service platform to search the song on.

        Examples
        --------
        `/play query: "50 cent - love me"`
        `/play query: "50 cent - love me" service: "soundcloud"`
        """
        player: Player = self.bot.wavelink.get_player(
            guild_id=interaction.guild.id, cls=Player, context=interaction
        )
        services = {
            "youtube": SearchService.ytsearch,
            "soundcloud": SearchService.scsearch,
            "youtubemusic": SearchService.ytmsearch,
            "spotify": SearchService.spsearch,
            "applemusic": SearchService.amsearch,
        }

        await interaction.response.defer()

        if not player.is_connected:
            await self.connect(interaction=interaction)

        query = query.strip("<>")
        if (
                not service.lower() == "youtubemusic"
                or service.lower() == "youtube"
                and not url_regex.match(query)
        ):
            query = f"{services[service.lower()]}:{query}"

        if not SOUNDCLOUD_URL_REGEX.match(query) and service.lower() == "soundcloud":
            query = f"{services[service.lower()]}:{query}"

        if not SPOTIFY_URL_REGEX.match(query) and service.lower() == "spotify":
            query = f"{services[service.lower()]}:{query}"

        if (
                SPOTIFY_URL_REGEX.match(query)
                or SOUNDCLOUD_URL_REGEX.match(query)
                or url_regex.match(query) or youtube_url_regex.match(query)
        ):
            #  If the query is a spotify, soundcloud or YouTube url, we can just play it directly.
            tracks = await self.bot.wavelink.get_tracks(query)

            if not tracks:
                return await interaction.edit_original_message(
                    content=f"{self.bot.icons['redtick']} No songs were found with that query. "
                            f"Please try again.",
                )

            if isinstance(tracks, wavelink.TrackPlaylist):
                for track in tracks.tracks:
                    track = Track(track.id, track.info, requester=interaction.author)
                    await player.queue.put(track)

                return await interaction.edit_original_message(
                    embed=disnake.Embed(
                        description=f'```ini\nAdded the playlist {tracks.data["playlistInfo"]["name"]}'
                                    f" with {len(tracks.tracks)} songs to the queue.\n```",
                        color=disnake.Colour.random(),
                    ).set_footer(
                        text=f"Requested by {interaction.author.name}",
                        icon_url=interaction.author.display_avatar.url,
                    )
                )
            else:
                track = Track(
                    tracks[0].id, tracks[0].info, requester=interaction.author
                )
                await interaction.edit_original_message(
                    content=f"\n{self.bot.icons['headphones']} Enqueued `{track.title}` to the Queue\n"
                )
                await player.queue.put(track)

            if not player.is_playing:
                await player.play_next_song()
                return

        tracks = await self.bot.wavelink.get_tracks(
            query
        )  # If the query is not a spotify or soundcloud url,
        # we need to search for it.

        if not tracks:
            return await interaction.edit_original_message(
                content=f"{self.bot.icons['redtick']} No songs were found with that query. "
                        f"Please try again.",
            )

        if isinstance(tracks, wavelink.TrackPlaylist):
            for track in tracks.tracks:
                track = Track(track.id, track.info, requester=interaction.author)
                await player.queue.put(track)

            await interaction.edit_original_message(
                embed=disnake.Embed(
                    description=f'```ini\nAdded the playlist {tracks.data["playlistInfo"]["name"]}'
                                f" with {len(tracks.tracks)} songs to the queue.\n```",
                    color=disnake.Colour.random(),
                ).set_footer(
                    text=f"Requested by {interaction.author.name}",
                    icon_url=interaction.author.display_avatar.url,
                )
            )
            if not player.is_playing:
                await player.play_next_song()
            return
        else:
            await interaction.edit_original_message(
                content=f"\n{self.bot.icons['headphones']} Please select a song to play.\n",
                view=SongSelectionView(
                    tracks=tracks[:11],
                    player=player,
                    bot=self.bot,
                    interaction=interaction,
                ),
            )
            return

    @play.autocomplete(option_name="service")
    async def play_service_autocomplete(
            self, interaction: disnake.ApplicationCommandInteraction, query: str
    ):
        """
        Autocomplete for the play command.

        Parameters
        ----------
        interaction: disnake.ApplicationCommandInteraction
            This parameter takes disnake.ApplicationCommandInteraction object, when this slash command is executed
            which creates an Interaction. This is not used.

        query: str
            The query to search for.

        Returns
        -------
        list
            A list of autocomplete options.
        """
        options = ["youtube", "soundcloud", "youtubemusic", "spotify"]
        return [option for option in options if query.lower() in options]

    @commands.slash_command(
        description="Switch the channel where the bot was first invoked."
    )
    async def switch_channel(
            self,
            interaction: disnake.ApplicationCommandInteraction,
            channel: disnake.TextChannel = Param(description="Channel to switch to."),
    ):
        """
        A command that will switch to a different channel and set it as the channel where the bot was invoked.

        This command is useful when you want to play music in a different channel than the one where the bot was
        invoked before.

        Parameters
        ----------
        interaction : disnake.ApplicationCommandInteraction
            This parameter takes disnake.ApplicationCommandInteraction object, when this slash command is executed
            which creates an Interaction.

        channel : disnake.TextChannel
            The channel where the bot will be invoked.

        Examples
        --------
        `/switch_channel channel: #general`
        """
        player: Player = self.bot.wavelink.get_player(
            guild_id=interaction.guild.id, cls=Player, context=interaction
        )
        if not player.is_connected:
            return await interaction.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['redtick']} `You must be connected to a voice channel.`",
                    colour=disnake.Colour.random(),
                ),
                delete_after=10,
            )
        if not self.is_author(interaction):
            await interaction.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['info']} Only `{player.dj} can switch channels.`",
                    color=disnake.Colour.random(),
                ),
                delete_after=10,
            )

        player.channel = channel
        await interaction.response.send_message(
            embed=disnake.Embed(
                description=f"{self.bot.icons['greentick']} `Successfully "
                            f"set {channel.mention} as the session channel.`",
                colour=disnake.Colour.random(),
            ),
            delete_after=10,
        )

    @commands.slash_command(description="Pause the current playing song.")
    async def pause(self, interaction: disnake.ApplicationCommandInteraction):
        """
        A command that will pause the music player, if it is playing a track.

        Parameters
        ----------
        interaction: disnake.ApplicationCommandInteraction
            This parameter takes disnake.ApplicationCommandInteraction object, when this slash command is executed
            which creates an Interaction.

        Examples
        --------
        `/pause`
        """
        player: Player = self.bot.wavelink.get_player(
            guild_id=interaction.guild.id, cls=Player, context=interaction
        )

        if not player.is_connected:
            return await interaction.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['redtick']} `You must be connected to a voice channel.`",
                    colour=disnake.Colour.random(),
                ),
                delete_after=10,
            )

        if not player.is_playing:
            return await interaction.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['redtick']} `There is no track playing right now.`",
                    colour=disnake.Colour.random(),
                )
            )

        if player.is_paused:
            return await interaction.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['redtick']} `The player is already paused.`",
                    colour=disnake.Colour.random(),
                ),
                delete_after=10,
            )

        if self.is_author(interaction):
            await interaction.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['info']} `{player.dj}` has paused the player.",
                    color=disnake.Colour.random(),
                ),
                delete_after=10,
            )
            player.pause_votes.clear()

            return await player.set_pause(True)

        required = self.vote_check(interaction)
        player.pause_votes.add(interaction.author)

        if len(player.pause_votes) >= required:
            await interaction.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['greentick']} `Vote to pause passed. Pausing player.`",
                    color=disnake.Colour.random(),
                ),
                delete_after=10,
            )
            player.pause_votes.clear()
            await player.set_pause(True)
        else:
            await interaction.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['info']} `{interaction.author} has voted to pause the player.`",
                    color=disnake.Colour.random(),
                ),
            )

    @commands.slash_command(description="Resumes a currently paused song.")
    async def resume(self, interaction: disnake.ApplicationCommandInteraction):
        """
        A command that will resume the music player if it is paused.

        Parameters
        ----------
        interaction : disnake.ApplicationCommandInteraction
            This parameter takes disnake.ApplicationCommandInteraction object, when this slash command is executed
            which creates an Interaction.

        Examples
        --------
        `/resume`
        """
        player: Player = self.bot.wavelink.get_player(
            guild_id=interaction.guild.id, cls=Player, context=interaction
        )

        if not player.is_connected:
            return await interaction.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['redtick']} `You must be connected to a voice channel.`",
                    colour=disnake.Colour.random(),
                ),
                delete_after=10,
            )

        if not player.is_playing:
            return await interaction.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['redtick']} `There is no track playing right now.`",
                    colour=disnake.Colour.random(),
                )
            )

        if not player.is_paused:
            return await interaction.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['redtick']} `The player is not paused.`",
                    colour=disnake.Colour.random(),
                ),
                delete_after=10,
            )

        if self.is_author(interaction):
            await interaction.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['info']} `{player.dj}` has resumed the player.",
                    color=disnake.Colour.random(),
                ),
                delete_after=10,
            )
            player.resume_votes.clear()

            return await player.set_pause(False)

        required = self.vote_check(interaction)
        player.resume_votes.add(interaction.author)

        if len(player.resume_votes) >= required:
            await interaction.response.send_message(
                "Vote to resume passed. Resuming player.", delete_after=10
            )
            player.resume_votes.clear()
            await player.set_pause(False)
        else:
            await interaction.response.send_message(
                f"{interaction.author} has voted to resume the song.",
            )

    @commands.slash_command(description="Skip the currently playing song.")
    async def skip(self, interaction: disnake.ApplicationCommandInteraction):
        """
        A command that will skip to the next song in queue. You need to have songs in queue to skip.
        The DJ of the song, can skip it without voting, else the members listening to the track, need to vote to skip.

        Parameters
        ----------
        interaction: disnake.ApplicationCommandInteraction
            This parameter takes disnake.ApplicationCommandInteraction object, when this slash command is executed
            which creates an Interaction.

        Examples
        --------
        `/skip`
        """
        player: Player = self.bot.wavelink.get_player(
            guild_id=interaction.guild.id, cls=Player, context=interaction
        )

        if not player.is_connected:
            return await interaction.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['redtick']} `You must be connected to a voice channel.`",
                    colour=disnake.Colour.random(),
                ),
                delete_after=10,
            )

        if self.is_author(interaction):
            await interaction.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['info']} `{player.dj}` has skipped the song.",
                    color=disnake.Colour.random(),
                ),
                delete_after=10,
            )
            player.skip_votes.clear()

            return await player.stop()

        required = self.vote_check(interaction)
        player.skip_votes.add(interaction.author)

        if len(player.skip_votes) >= required:
            await interaction.response.send_message(
                "Vote to skip passed. Skipping song.", delete_after=10
            )
            player.skip_votes.clear()
            await player.stop()
        else:
            await interaction.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['info']} `{interaction.author}` has voted to skip the song.",
                    color=disnake.Colour.random(),
                ),
            )

    @commands.slash_command(
        description="Stop the currently playing song and the music player."
    )
    async def stop(self, interaction: disnake.ApplicationCommandInteraction):
        """
        A command that will stop the currently playing song and the music player and only the DJ can use this command.

        Parameters
        ----------
        interaction: disnake.ApplicationCommandInteraction
            This parameter takes disnake.ApplicationCommandInteraction object, when this slash command is executed
            which creates an Interaction.

        Examples
        --------
        `/stop`
        """
        player: Player = self.bot.wavelink.get_player(
            guild_id=interaction.guild.id, cls=Player, context=interaction
        )

        if not player.is_connected:
            return await interaction.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['redtick']} `You must be connected to a voice channel.`",
                    colour=disnake.Colour.random(),
                ),
                delete_after=10,
            )

        if not player.is_playing:
            return await interaction.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['redtick']} `There is no track playing right now.`",
                    colour=disnake.Colour.random(),
                )
            )

        if self.is_author(interaction):
            await interaction.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['info']} `{player.dj}` has stopped the player.",
                    color=disnake.Colour.random(),
                ),
                delete_after=10,
            )
            return await player.teardown()

        required = self.vote_check(interaction)
        player.stop_votes.add(interaction.author)

        if len(player.stop_votes) >= required:
            await interaction.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['info']} Vote passed, stopping the player.",
                    color=disnake.Colour.random(),
                )
            )
            await player.teardown()
        else:
            await interaction.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['info']} `{interaction.author}` has voted to stop the song.",
                    color=disnake.Colour.random(),
                )
            )

    @commands.slash_command(description="Disconnect the bot and stop the music player.")
    async def disconnect(self, interaction: disnake.ApplicationCommandInteraction):
        """
        A command that will stop and clear the music player and disconnect the bot.

        Parameters
        ----------
        interaction: disnake.ApplicationCommandInteraction
            This parameter takes disnake.ApplicationCommandInteraction object, when this slash command is executed
            which creates an Interaction.

        Examples
        --------
        `/disconnect`
        """
        player: Player = self.bot.wavelink.get_player(
            guild_id=interaction.guild.id, cls=Player, context=interaction
        )

        if not player.is_connected:
            return await interaction.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['redtick']} `You must be connected to a voice channel.`",
                    colour=disnake.Colour.random(),
                ),
                delete_after=10,
            )

        if not self.is_author(interaction):
            return await interaction.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['info']} Only `{player.dj}` can disconnect the player.",
                    color=disnake.Colour.random(),
                ),
                delete_after=10,
            )
        await interaction.response.send_message(
            embed=disnake.Embed(
                description=f"{self.bot.icons['info']} `{player.dj}` has disconnected the player.",
                color=disnake.Colour.random(),
            )
        )
        await player.teardown()

    @commands.slash_command(description="Change the players volume, between 1 and 100.")
    async def volume(
            self,
            interaction: disnake.ApplicationCommandInteraction,
            vol: int = commands.Range[1, 100]
    ):
        """
        A command that will alter the volume of the music player, between 1 and 100.

        Parameters
        ----------
        interaction: disnake.ApplicationCommandInteraction
            This parameter takes disnake.ApplicationCommandInteraction object, when this slash command is executed
            which creates an Interaction.

        vol: int
            The volume to set the player to.

        Examples
        --------
        `/volume vol: 50`
        """
        player: Player = self.bot.wavelink.get_player(
            guild_id=interaction.guild.id, cls=Player, context=interaction
        )

        if not player.is_connected:
            return await interaction.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['redtick']} `You must be connected to a voice channel.`",
                    colour=disnake.Colour.random(),
                )
            )

        if not player.is_playing:
            return await interaction.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['redtick']} `There is no track playing right now.`",
                    colour=disnake.Colour.random(),
                )
            )

        if not self.is_author(interaction):
            return await interaction.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['info']} Only the `{player.dj}` can change the volume of this song.",
                    color=disnake.Colour.random(),
                )
            )

        if not 0 < vol < 101:
            return await interaction.response.send(
                f"{self.bot.icons['info']} Please enter a value between 1 and 100."
            )

        await player.set_volume(vol)
        await interaction.response.send_message(
            embed=disnake.Embed(
                description=f"{self.bot.icons['greentick']} Set the volume "
                            f"to **{vol}**%",
                colour=disnake.Colour.random(),
            )
        )

    @commands.slash_command()
    async def loop(self, interaction: disnake.ApplicationCommandInteraction):
        pass

    @loop.sub_command(description="Loops the current playing track.")
    async def on(self, interaction: disnake.ApplicationCommandInteraction):
        """
        A command that will loop your specific music track and keep playing it repeatedly.

        Parameters
        ----------
        interaction: disnake.ApplicationCommandInteraction
            This parameter takes disnake.ApplicationCommandInteraction object, when this slash command is executed
            which creates an Interaction.

        Examples
        --------
        `/loop on` - Loops the current track.
        """
        player: Player = self.bot.wavelink.get_player(
            guild_id=interaction.guild.id, cls=Player, context=interaction
        )

        if not player.is_connected:
            return await interaction.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['redtick']} `You must be connected to a voice channel.`",
                    colour=disnake.Colour.random(),
                ),
                delete_after=10,
            )

        if not player.is_playing:
            return await interaction.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['redtick']} `There is no track playing right now.`",
                    colour=disnake.Colour.random(),
                )
            )

        if not self.is_author(interaction):
            return await interaction.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['info']} Only the `{player.dj}` can loop this song.",
                    color=disnake.Colour.random(),
                )
            )

        if player.loop is False:
            await interaction.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['greentick']} Looped the current track.",
                    color=disnake.Colour.random(),
                )
            )
            player.loop = True
            return
        if player.loop is True:
            return await interaction.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['greentick']} This track is on loop already.",
                    color=disnake.Colour.random(),
                )
            )

    @loop.sub_command(description="Stops looping the current playing track.")
    async def off(self, interaction: disnake.ApplicationCommandInteraction):
        """
        A command that will loop your specific music track and keep playing it repeatedly.

        Parameters
        ----------
        interaction: disnake.ApplicationCommandInteraction
            This parameter takes disnake.ApplicationCommandInteraction object, when this slash command is executed
            which creates an Interaction.

        Examples
        --------
        `/loop off` - un-Loops the current track.
        """
        player: Player = self.bot.wavelink.get_player(
            guild_id=interaction.guild.id, cls=Player, context=interaction
        )

        if not player.is_connected:
            return await interaction.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['redtick']} `You must be connected to a voice channel.`",
                    colour=disnake.Colour.random(),
                ),
                delete_after=10,
            )

        if not player.is_playing:
            return await interaction.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['redtick']} `There is no track playing right now.`",
                    colour=disnake.Colour.random(),
                )
            )

        if not self.is_author(interaction):
            return await interaction.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['info']} Only the `{player.dj}` can loop this song.",
                    color=disnake.Colour.random(),
                )
            )

        if player.loop is False:
            return await interaction.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['greentick']} The track is not on loop.",
                    color=disnake.Colour.random(),
                )
            )
        if player.loop is True:
            await interaction.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['greentick']} Un-looped the current track.",
                    color=disnake.Colour.random(),
                )
            )
            player.loop = False
            return

    @commands.slash_command(description="Show lyrics of the current playing song.")
    async def lyrics(self, interaction: disnake.ApplicationCommandInteraction):
        """
        A command that will show the lyrics of the current playing song or the name of the song you want lyrics
        for, if you explicitly specify it.

        Parameters
        ----------
        interaction : disnake.ApplicationCommandInteraction
            This parameter takes disnake.ApplicationCommandInteraction object, when this slash command is executed
            which creates an Interaction.

        Examples
        --------
        `/lyrics`
        """
        player: Player = self.bot.wavelink.get_player(
            guild_id=interaction.guild.id, cls=Player, context=interaction
        )

        name = player.now.title

        if not player.is_connected:
            return await interaction.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['redtick']} `You must be connected to a voice channel.`",
                    colour=disnake.Colour.random(),
                )
            )
        lyrics_query = (
            f"https://some-random-api.ml/lyrics?title={name}-{player.now.author}"
        )
        resp = await self.bot.session.get(lyrics_query)

        if resp.status != 200:
            return await interaction.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['redtick']} `Lyrics for this song is not found.`",
                    colour=disnake.Colour.random(),
                ),
                delete_after=10,
            )

        if not player.is_playing:
            return await interaction.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['redtick']} `There is no track playing right now.`",
                    colour=disnake.Colour.random(),
                )
            )

        data = await resp.json()
        await interaction.response.send_message(content="Generating lyrics....", delete_after=5)

        lyrics = data["lyrics"]
        content = WrapText(lyrics, length=1000)
        pag = LyricsPaginator(
            lyrics=content, ctx=interaction, thumbnail=player.current.thumbnail
        )
        await pag.start()

    @commands.slash_command(description="Add a Filter to the player.")
    async def filter(self, interaction: disnake.ApplicationCommandInteraction):
        """
        A command that can add Filter to the music player of your choice.
        You will be asked to select between filters.
        There are five inbuilt filters:

        1.) Tremolo -> A Tremolo filter.
        2.) Vibrato -> A vibrato filter.
        3.) ExtremeBass -> A bass boost filter.
        4.) 8D -> An 8D audio filter.
        5.) Vibrato -> A vibrato filter.

        Parameters
        ----------
        interaction : disnake.ApplicationCommandInteraction
            This parameter takes disnake.ApplicationCommandInteraction object, when this slash command is executed which
            creates an Interaction.

        Examples
        --------
        `/filter`
        """

        player: Player = self.bot.wavelink.get_player(
            guild_id=interaction.guild.id, cls=Player, context=interaction
        )

        if not player.is_connected:
            return await interaction.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['redtick']} `You must be connected to a voice channel.`",
                    colour=disnake.Colour.random(),
                )
            )

        if not self.is_author(interaction):
            return await interaction.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['info']} Only the `{player.dj}` can add filters to the player.",
                    color=disnake.Colour.random(),
                )
            )

        if not player.is_playing:
            return await interaction.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['redtick']} `There is no track playing right now.`",
                    colour=disnake.Colour.random(),
                )
            )

        await interaction.response.send_message(
            content="Select a Filter:",
            view=FilterView(interaction=interaction, player=player),
        )

    @commands.slash_command(description="Create and set a custom filter.")
    async def create_filter(self, interaction: disnake.ApplicationCommandInteraction):
        pass

    @create_filter.sub_command(
        description="Add a custom filter, built from channel_mix."
    )
    async def channel_mix(
            self,
            interaction: disnake.ApplicationCommandInteraction,
            left_to_right: float = Param(
                description="Left to Right", default=0.5, ge=0.0, le=10.0
            ),
            right_to_left: float = Param(
                description="Right to Left", default=0.5, ge=0.0, le=10.0
            ),
            right_to_right: float = Param(
                description="Right to Right", default=0.5, ge=0.0, le=10.0
            ),
            left_to_left: float = Param(
                description="Left to Left", default=0.5, ge=0.0, le=10.0
            ),
    ):

        """
        Filter which manually adjusts the panning of the audio, which can make
        for some cool effects when done correctly.
        Remember, this can adversely affect the audio quality.

        Parameters
        ----------
        interaction : disnake.ApplicationCommandInteraction
            This parameter takes disnake.ApplicationCommandInteraction object, when this slash command is executed which
            creates an Interaction.

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
            guild_id=interaction.guild.id, cls=Player, context=interaction
        )

        if not player.is_connected:
            return await interaction.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['redtick']} `You must be connected to a voice channel.`",
                    colour=disnake.Colour.random(),
                ),
                delete_after=10,
            )

        if not player.is_playing:
            return await interaction.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['redtick']} `There is no track playing right now.`",
                    colour=disnake.Colour.random(),
                )
            )

        if not self.is_author(interaction):
            return await interaction.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['info']} Only the `{player.dj}` can set the filter to the player.",
                    color=disnake.Colour.random(),
                )
            )
        try:
            filter_ = wavelink.BaseFilter.build_from_channel_mix(
                left_to_left=left_to_left,
                left_to_right=left_to_right,
                right_to_left=right_to_left,
                right_to_right=right_to_right,
            )
        except ValueError as e:
            return await interaction.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['redtick']} `{e}`",
                    colour=disnake.Colour.random(),
                )
            )

        await player.set_filter(filter_)
        await interaction.response.send_message(
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
            interaction: disnake.ApplicationCommandInteraction,
            speed: float = Param(description="Speed", default=1.0, ge=0.0),
            pitch: float = Param(description="Pitch", default=1.0, ge=0.0),
            rate: float = Param(description="Rate", default=1.0, ge=0.0),
    ):
        """
        Filter which changes the speed and pitch of a track.
        You can make some very nice effects with this filter.

         Parameters
         ----------
         interaction : disnake.ApplicationCommandInteraction
             This parameter takes disnake.ApplicationCommandInteraction object, when this slash command is executed
              which creates an Interaction.

         speed : float
             The speed of the audio.

         pitch : float
             The pitch of the audio.

         rate : float
             The rate of the audio.

        Examples
        --------
        `/create_filter time_scale speed=1.5 pitch=1.5 rate=1.5`
        """

        player: Player = self.bot.wavelink.get_player(
            guild_id=interaction.guild.id, cls=Player, context=interaction
        )

        if not player.is_connected:
            return await interaction.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['redtick']} `You must be connected to a voice channel.`",
                    colour=disnake.Colour.random(),
                ),
                delete_after=10,
            )

        if not player.is_playing:
            return await interaction.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['redtick']} `There is no track playing right now.`",
                    colour=disnake.Colour.random(),
                )
            )

        if not self.is_author(interaction):
            return await interaction.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['info']} Only the `{player.dj}` can set the filter to the player.",
                    color=disnake.Colour.random(),
                )
            )
        try:
            filter_ = wavelink.BaseFilter.build_from_timescale(
                speed=speed, pitch=pitch, rate=rate
            )
        except FilterInvalidArgument as e:
            return await interaction.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['redtick']} `{e}`",
                    colour=disnake.Colour.random(),
                )
            )

        await player.set_filter(filter_)
        await interaction.response.send_message(
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
            interaction: disnake.ApplicationCommandInteraction,
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
        interaction : disnake.ApplicationCommandInteraction
             This parameter takes disnake.ApplicationCommandInteraction object, when this slash command is executed
             which creates an Interaction.

        sin_offset : float
            The sin offset of the filter.

        sin_scale : float
            The sin scale of the filter.

        cos_offset : float
            The cos offset of the filter.

        cos_scale : float
            The cos scale of the filter.

        tan_offset : float
            The tan offset of the filter.

        tan_scale : float
            The tan scale of the filter.

        offset : float
            The main offset of the filter.

        scale : float
            The main scale of the filter.

        Examples
        --------
        `/create_filter distortion sin_offset=0.5 sin_scale=1.5 cos_offset=0.5 cos_scale=1.5
        tan_offset=0.5 tan_scale=1.5 offset=0.5 scale=1.5`
        """

        player: Player = self.bot.wavelink.get_player(
            guild_id=interaction.guild.id, cls=Player, context=interaction
        )

        if not player.is_connected:
            return await interaction.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['redtick']} `You must be connected to a voice channel.`",
                    colour=disnake.Colour.random(),
                ),
                delete_after=10,
            )

        if not player.is_playing:
            return await interaction.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['redtick']} `There is no track playing right now.`",
                    colour=disnake.Colour.random(),
                )
            )

        if not self.is_author(interaction):
            return await interaction.response.send_message(
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
        await interaction.response.send_message(
            embed=disnake.Embed(
                description=f"{self.bot.icons['greentick']} `Filter set to:` {filter_.name}",
                colour=disnake.Colour.random(),
            )
        )

    @commands.slash_command(description="Display the player's queued songs.")
    async def queue(self, interaction: disnake.ApplicationCommandInteraction):
        pass

    @queue.sub_command(description="Display the player's queued songs.")
    async def show(self, interaction: disnake.ApplicationCommandInteraction):
        """
        A command that will show all the songs that queued in the music player. It has pagination,
        so it's easy for you to browse.

        Parameters
        ----------
        interaction : disnake.ApplicationCommandInteraction
            This parameter takes disnake.ApplicationCommandInteraction object, when this slash command is executed
            which creates an Interaction.

        Examples
        --------
         `/queue show`
        """
        player: Player = self.bot.wavelink.get_player(
            guild_id=interaction.guild.id, cls=Player, context=interaction
        )

        if not player.is_connected:
            return await interaction.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['redtick']} `You must be connected to a voice channel.`",
                    colour=disnake.Colour.random(),
                ),
                delete_after=10,
            )

        if player.queue.qsize() == 0:
            return await interaction.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['info']} There are no more songs "
                                f"in the queue.",
                    colour=disnake.Colour.random(),
                ),
            )

        entries = []
        for track in player.queue._queue:
            entries.append(
                f"[{track.title}]({track.uri}) - `{track.author}` - "
                f"`{humanize.precisedelta(datetime.timedelta(milliseconds=track.length))}`"
            )

        await interaction.response.send_message("Loading...")

        paginator = QueuePages(entries=entries, ctx=interaction)

        await paginator.start()

    @queue.sub_command(description="Clear the player's queued songs.")
    async def clear(self, interaction: disnake.ApplicationCommandInteraction):
        """
        A command that will clear the entire queue of the current music player instance.

        Parameters
        ----------
        interaction : disnake.ApplicationCommandInteraction
            This parameter takes disnake.ApplicationCommandInteraction object, when this slash command is executed which
            creates an Interaction.

        Examples
        --------
        `/queue clear`
        """
        player: Player = self.bot.wavelink.get_player(
            guild_id=interaction.guild.id, cls=Player, context=interaction
        )

        if not player.is_connected:
            return await interaction.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['redtick']} `You must be connected to a voice channel.`",
                    colour=disnake.Colour.random(),
                ),
                delete_after=10,
            )

        if player.queue.qsize() == 0:
            return await interaction.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['info']} Queue is empty.",
                    color=disnake.Colour.random(),
                )
            )

        if self.is_author(interaction):
            await interaction.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['info']} `{player.dj}` has cleared the queue.",
                    color=disnake.Colour.random(),
                )
            )

            player.clear_votes.clear()
            player.queue.clear()
            return

        required = self.vote_check(interaction)
        player.clear_votes.add(interaction.author)

        if len(player.shuffle_votes) >= required:
            await interaction.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['info']} Vote passed, clearing the queue.",
                    color=disnake.Colour.random(),
                )
            )

            player.clear_votes.clear()
            player.queue.clear()
        else:
            return await interaction.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['info']} `{interaction.author}` has voted to clear the queue.",
                    color=disnake.Colour.random(),
                )
            )

    @queue.sub_command(description="Remove a song from the queue by its index.")
    async def remove(
            self,
            interaction: disnake.ApplicationCommandInteraction,
            index: int = Param(description="The index of the song to remove."),
    ):
        """
        A command that will remove the song based on its index/number from the queue.

        Parameters
        ----------
        interaction : disnake.ApplicationCommandInteraction
            This parameter takes disnake.ApplicationCommandInteraction object, when this slash command is executed which
            creates an Interaction.

        index : int
            The index of the song to remove.

        Examples
        --------
         `/queue remove index: 1`
        """
        player: Player = self.bot.wavelink.get_player(
            guild_id=interaction.guild.id, cls=Player, context=interaction
        )

        if not player.is_connected:
            return await interaction.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['redtick']} `You must be connected to a voice channel.`",
                    colour=disnake.Colour.random(),
                )
            )

        if not player.is_playing:
            return await interaction.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['redtick']} `There is no song playing right now.`",
                    colour=disnake.Colour.random(),
                )
            )
        if player.queue.qsize() == 0:
            return await interaction.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['info']} There are no more songs "
                                f"in the queue.",
                    colour=disnake.Colour.random(),
                ),
            )
        if not self.is_author(interaction):
            return await interaction.channel.send(
                embed=disnake.Embed(
                    description=f"Only {player.dj} can use this command.",
                    color=disnake.Colour.random(),
                )
            )
        if index > player.queue.qsize():
            return await interaction.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['redtick']} `That is not a valid index.`",
                    colour=disnake.Colour.random(),
                )
            )
        song_to_remove = index - 1
        player.queue.remove(song_to_remove)
        await interaction.response.send_message(
            embed=disnake.Embed(
                description=f"{self.bot.icons['greentick']} `Removed song from queue.`",
                colour=disnake.Colour.random(),
            )
        )

    @queue.sub_command(description="Shuffle the queue.")
    async def shuffle(self, interaction: disnake.ApplicationCommandInteraction):
        """
        A command that will shuffle the entire queue of the current music player instance.
        You need at least 3 songs or more in queue in order to shuffle properly.

        Parameters
        ----------
        interaction: disnake.ApplicationCommandInteraction
            This parameter takes disnake.ApplicationCommandInteraction object, when this slash command is executed which
            creates an Interaction.

        Examples
        --------
        `/queue shuffle`
        """
        player: Player = self.bot.wavelink.get_player(
            guild_id=interaction.guild.id, cls=Player, context=interaction
        )

        if not player.is_connected:
            return await interaction.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['redtick']} `You must be connected to a voice channel.`",
                    colour=disnake.Colour.random(),
                ),
                delete_after=10,
            )

        if player.queue.qsize() < 3:
            return await interaction.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['info']} Add more songs before shuffling.",
                    color=disnake.Colour.random(),
                )
            )

        if self.is_author(interaction):
            await interaction.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['info']} `{player.dj}` has shuffled the queue.",
                    color=disnake.Colour.random(),
                )
            )

            player.shuffle_votes.clear()
            return player.queue.shuffle()

        required = self.vote_check(interaction)
        player.shuffle_votes.add(interaction.author)

        if len(player.shuffle_votes) >= required:
            await interaction.channel.send(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['info']} Vote passed, shuffling songs.",
                    color=disnake.Colour.random(),
                )
            )

            player.shuffle_votes.clear()
            player.queue.shuffle()
        else:
            return await interaction.channel.send(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['info']} `{interaction.author}` has voted to shuffle the queue.",
                    color=disnake.Colour.random(),
                )
            )

    @commands.slash_command(description="Show the current playing song")
    async def nowplaying(self, interaction: disnake.ApplicationCommandInteraction):
        """
        A command that will show the information about the track that has been playing.

        Parameters
        ----------
        interaction : disnake.ApplicationCommandInteraction
            This parameter takes disnake.ApplicationCommandInteraction object, when this slash command is executed
            which creates an Interaction.

        Examples
        --------
         `/nowplaying`
        """
        player: Player = self.bot.wavelink.get_player(
            guild_id=interaction.guild.id, cls=Player, context=interaction
        )

        if not player.is_connected:
            return await interaction.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['redtick']} `You must be connected to a voice channel.`",
                    colour=disnake.Colour.random(),
                )
            )

        if not player.is_playing:
            return await interaction.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['redtick']} `There is no song playing right now.`",
                    colour=disnake.Colour.random(),
                )
            )

        embed = await player.make_song_embed()  # shows the song embed.
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @commands.slash_command(description="Save the current playing song in your dms.")
    async def save(self, interaction: disnake.ApplicationCommandInteraction):
        """
        A command that will show the information about the track that has been playing and send it in your dms,
        if possible, so make sure that you have kept your dms open.

        Parameters
        ----------
        interaction : disnake.ApplicationCommandInteraction
            This parameter takes disnake.ApplicationCommandInteraction object, when this slash command is executed which
            creates an Interaction.

        Examples
        --------
         `/save`
        """
        player: Player = self.bot.wavelink.get_player(
            guild_id=interaction.guild.id, cls=Player, context=interaction
        )

        if not player.is_connected:
            return await interaction.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['redtick']} `You must be connected to a voice channel.`",
                    colour=disnake.Colour.random(),
                )
            )

        if not player.is_playing:
            return await interaction.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['redtick']} `There is no song playing right now.`",
                    colour=disnake.Colour.random(),
                )
            )

        embed = await player.make_song_embed()  # shows the song embed.
        await interaction.response.send_message(
            content="I have dm'ed you something!", ephemeral=True
        )
        try:
            await interaction.author.send(embed=embed)
        except disnake.Forbidden:
            return await interaction.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['redtick']} `I don't have permission to send messages in your dms.`",
                    colour=disnake.Colour.random(),
                ),
                ephemeral=True,
            )

    @commands.slash_command(description="Seek to a specific time in the song.")
    async def seek(
            self,
            interaction: disnake.ApplicationCommandInteraction,
            position: str = Param(
                description="The time position to seek to. For eg: /seek 3:56"
            ),
    ):
        """
        A command that will seek aka skip to a specific part of a track in a song that has been playing.

        Parameters
        ----------
        interaction : disnake.ApplicationCommandInteraction
            This parameter takes disnake.ApplicationCommandInteraction object, when this slash command is executed which
            creates an Interaction.

        position : str
            The time position to seek to. For eg: /seek 3:56

        Examples
        --------
        `/seek position: 3:56` -> This will skip to 3 minutes and 56 seconds in the playing track.
        """
        player: Player = self.bot.wavelink.get_player(
            guild_id=interaction.guild.id, cls=Player, context=interaction
        )
        time_regex = r"([0-9]{1,2})[:ms](([0-9]{1,2})s?)?"

        if not player.is_connected:
            return await interaction.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['redtick']} `You must be connected to a voice channel.`",
                    colour=disnake.Colour.random(),
                )
            )

        if not player.is_playing:
            return await interaction.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['redtick']} `There is no song playing right now.`",
                    colour=disnake.Colour.random(),
                )
            )
        if player.is_paused:
            return await interaction.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['redtick']} `There player is paused right now, resume it in order to "
                                f"seek.`",
                    colour=disnake.Colour.random(),
                )
            )

        if not self.is_author(interaction):
            return await interaction.channel.send(
                embed=disnake.Embed(
                    description=f"Only {player.dj} can use this command.",
                    color=disnake.Colour.random(),
                )
            )

        if not (match := re.match(time_regex, position)):
            await interaction.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['greentick']} `{position} is not a valid time format.`"
                )
            )
        if match.group(3):
            secs = (int(match.group(1)) * 60) + (int(match.group(3)))
        else:
            secs = int(match.group(1))

        await player.seek(secs * 1000)
        await interaction.response.send_message(
            embed=disnake.Embed(
                description=f"{self.bot.icons['greentick']} Successfully seeked to {secs} seconds.",
                colour=disnake.Colour.random(),
            )
        )

    @commands.slash_command(
        description="Swap the current DJ to another member in the voice channel."
    )
    async def swap_dj(
            self,
            interaction: disnake.ApplicationCommandInteraction,
            member: disnake.Member = Param(description="The member to switvj to"),
    ):
        """
        A command that will switch the player's DJ to another member in the same voice channel.

        Parameters
        ----------
        interaction : disnake.ApplicationCommandInteraction
            This parameter takes disnake.ApplicationCommandInteraction object, when this slash command is executed which creates an Interaction.

        member: disnake.Member
            The member to swap to.

        Examples
        --------
        `/swap_dj member: @Member` -> This will switch the player's DJ to the member specified.
        """
        player: Player = self.bot.wavelink.get_player(
            guild_id=interaction.guild.id, cls=Player, context=interaction
        )

        if not player.is_connected:
            return await interaction.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['redtick']} `You must be connected to a voice channel.`",
                    colour=disnake.Colour.random(),
                )
            )

        if not self.is_author(interaction):
            return await interaction.channel.send(
                embed=disnake.Embed(
                    description=f"Only {player.dj} can use this command.",
                    color=disnake.Colour.random(),
                )
            )

        members = self.bot.get_channel(int(player.channel_id)).members

        if member and member not in members:
            return await interaction.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['info']} `{member}` is not currently in voice, "
                                f"so they cannot be a DJ."
                ),
            )

        if member and member == player.dj:
            return await interaction.response.send_message(
                "Cannot swap DJ to the current DJ... :)",
            )

        if len(members) <= 2:
            return await interaction.channel.send(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['redtick']} `{member}` No more members to swap to."
                ),
                color=disnake.Colour.red(),
            )

        if member:
            player.dj = member
            return await interaction.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['info']} `{member}` is now a DJ."
                ),
            )

        for m in members:
            if m == player.dj or m.bot:
                continue
            else:
                player.dj = m
                return await interaction.response.send_message(
                    embed=disnake.Embed(
                        description=f"{self.bot.icons['info']} `{member}` is now a DJ.",
                        colour=disnake.Colour.random(),
                    )
                )


def setup(bot):
    bot.add_cog(Music(bot))
