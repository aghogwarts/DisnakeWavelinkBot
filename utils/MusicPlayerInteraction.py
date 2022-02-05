#  -*- coding: utf-8 -*-
import asyncio
import datetime
import itertools
import math
import random
import sys
import traceback
import typing

from disnake.ui import Item
from loguru import logger
import async_timeout
import disnake
import humanize

import wavelink
from core.MusicBot import Bot
from utils.helpers import LyricsPaginator, ErrorView
from utils.paginators import RichPager, ViewPages, WrapText


class Track(wavelink.Track):
    """
    Wavelink Track object with a requester attribute.
    """

    __slots__ = ("requester",)

    def __init__(self, *args, **kwargs):
        super().__init__(*args)

        self.requester = kwargs.get("requester")


class Queue(asyncio.Queue):
    """
    Custom Queue Class.
    """

    def __getitem__(self, item):
        if isinstance(item, slice):
            return list(itertools.islice(self._queue, item.start, item.stop, item.step))  # type: ignore
        else:
            return self._queue[item]  # type: ignore

    def __iter__(self):
        return self._queue.__iter__()  # type: ignore

    def __len__(self):
        return self.qsize()

    def count(self):
        """
        A method that counts the number of tracks in the queue.
        """
        return len(self._queue)  # type: ignore

    def __repr__(self):
        return f"<Queue size: {self.qsize()}>"

    def clear(self):
        """
        A method that clears the queue.
        """
        self._queue.clear()  # type: ignore

    def shuffle(self):
        """
        A method that shuffles the queue.
        """
        random.shuffle(self._queue)  # type: ignore

    def remove(self, index: int):
        """
        A method that removes a track from the queue.
        """
        del self._queue[index]  # type: ignore


class Player(wavelink.Player):
    """
    Wavelink music player class.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.context: disnake.ApplicationCommandInteraction = kwargs.get("context")
        if self.context:
            self.dj: disnake.Member = self.context.author

        self.queue = Queue()
        self.menu: disnake.Message = None  # type: ignore
        try:
            self.channel = self.context.channel
        except AttributeError:
            pass
        self._loop = False

        self.waiting = False
        self.updating = False
        self.now = None

        self.pause_votes = set()
        self.resume_votes = set()
        self.skip_votes = set()
        self.shuffle_votes = set()
        self.stop_votes = set()
        self.clear_votes = set()

    async def play_next_song(self) -> None:
        """
        Method which plays the next song in the queue.
        """
        if self.is_playing or self.waiting:
            return

        # Clear the votes for a new song...
        self.pause_votes.clear()
        self.resume_votes.clear()
        self.skip_votes.clear()
        self.shuffle_votes.clear()
        self.stop_votes.clear()

        if not self._loop:

            try:
                self.waiting = True
                with async_timeout.timeout(120):
                    track = await self.queue.get()
                    self.now = track
                await self.play(track)
                self.waiting = False

                # Start our song menu
                await self.songmenucontroller()
            except asyncio.TimeoutError:
                # No music has been played for 2 minutes, cleanup and disconnect.
                return await self.teardown()
        if self._loop:
            track = self.now
            await self.play(track)
            await self.songmenucontroller()

    async def songmenucontroller(self) -> None:
        """
        Method which handles the song menu.
        """
        if self.updating:
            return

        self.updating = True

        if not self.menu:
            self.menu = await self.channel.send(
                embed=await self.make_song_embed(),
                view=MenuControllerView(self, self.context, bot=self.bot),
            )

        elif not await self.is_menu_available():
            try:
                await self.menu.delete()
            except disnake.HTTPException as e:
                logger.warning(f"Failed to delete menu message: {e}")
            except AttributeError as e:
                logger.warning(f"Failed to delete menu message: {e}")

            await self.channel.send(
                embed=await self.make_song_embed(),
                view=MenuControllerView(self, self.context, bot=self.bot),
            )

        else:
            embed = await self.make_song_embed()
            await self.channel.send(
                content=None,
                embed=embed,
                view=MenuControllerView(self, self.context, bot=self.bot),
            )

        self.updating = False

    async def make_song_embed(self) -> typing.Optional[disnake.Embed]:
        """
        Method which creates the song embed containing the information about the song.

        Returns
        -------
        typing.Optional[`disnake.Embed`]
            A disnake.Embed object containing the song information.
        """
        track: Track = self.current
        if not track:
            return None

        channel = self.bot.get_channel(int(self.channel_id))
        position = divmod(self.position, 60000)
        length = divmod(self.now.length, 60000)
        mode = "yes" if self._loop else "off"

        embed = disnake.Embed(
            description=f"```css\nNow Playing:\n**{track.title}**```",
            colour=disnake.Colour.random(),
        )
        try:
            embed.set_thumbnail(url=track.thumbnail)
        except disnake.errors.HTTPException:
            pass

        embed.add_field(
            name="Duration",
            value=f"`{humanize.precisedelta(datetime.timedelta(milliseconds=int(track.length)))}`",
        )
        embed.add_field(name="Volume", value=f"**`{self.volume}%`**")
        embed.add_field(
            name="Position",
            value=f"`{int(position[0])}:{round(position[1] / 1000):02}/{int(length[0])}:{round(length[1] / 1000):02}`",
        )
        embed.add_field(name="Track on loop?", value=f"**`{mode}`**")
        embed.add_field(name="Channel", value=f"**`{channel}`**")
        embed.add_field(name="DJ", value=self.dj.mention)
        embed.add_field(name="Video URL", value=f"[Click Here!]({track.uri})")
        embed.add_field(name="Author", value=f"`{track.author}`")
        embed.set_footer(
            text=f"Requested By {track.requester}",
            icon_url=track.requester.display_avatar,
        )

        return embed

    async def is_menu_available(self) -> bool:
        """
        Method which checks whether the player controller should be remade or updated.

        Returns
        -------
        bool
            Whether the player controller should be remade or updated.
        """
        try:
            async for message in self.context.channel.history(limit=10):
                if message.id == self.menu.message.id:
                    return True
        except (disnake.HTTPException, AttributeError):
            return False

        return False

    async def teardown(self):
        """
        Method which handles the teardown(clearing and disconnection) of the player.
        """
        try:
            await self.menu.delete()
        except disnake.HTTPException as e:
            logger.warning(f"Failed to delete menu message: {e}")
        except AttributeError:
            logger.warning("Failed to delete menu message: No menu message")

        try:
            await self.destroy()
        except KeyError as e:
            logger.warning(f"Failed to destroy player: {e}")

    @property
    def loop(self):
        """
        Property which returns the loop state of the player.
        """
        return self._loop

    @loop.setter
    def loop(self, value: bool = False) -> None:
        """
        Property which sets the loop state of the player.

        Parameters
        ----------
        value : bool
            The value to set the loop to.
        """
        self._loop = value


class QueuePages(ViewPages):
    """
    A simple paginator interface that is a subclass of :class: ViewPages.
    This class is used to paginate the queue.
    """

    def __init__(
        self, entries, ctx: disnake.ApplicationCommandInteraction, per_page: int = 5
    ):
        super().__init__(RichPager(entries, per_page=per_page), ctx=ctx)
        self.embed = disnake.Embed(
            title=f"**{len(entries)}** songs in Queue...",
            colour=disnake.Colour.random(),
        ).set_footer(
            text=f"Requested By {ctx.author}", icon_url=ctx.author.display_avatar.url
        )


class MenuControllerView(disnake.ui.View):
    def __init__(
        self,
        player: Player,
        interaction: disnake.ApplicationCommandInteraction,
        bot: Bot,
    ):
        super().__init__(timeout=None)
        self.player = player
        self.interaction = interaction
        self.bot = bot
        self.controller = MenuController(
            self.player, bot=self.bot, interaction=self.interaction
        )

    @disnake.ui.button(label="⏸️", style=disnake.ButtonStyle.primary)
    async def pause_song(
        self, button: disnake.Button, interaction: disnake.ApplicationCommandInteraction
    ):
        """
        A button that pauses the song.
        """

        await self.controller.pause(interaction=interaction)

    @disnake.ui.button(label="▶", style=disnake.ButtonStyle.primary)
    async def resume_song(
        self, button: disnake.Button, interaction: disnake.ApplicationCommandInteraction
    ):
        """
        A button that resumes the song.
        """

        await self.controller.resume(interaction=interaction)

    @disnake.ui.button(label="⏩", style=disnake.ButtonStyle.primary)
    async def skip_song(
        self, button: disnake.Button, interaction: disnake.ApplicationCommandInteraction
    ):
        """
        A button that skips the song.
        """

        await self.controller.skip(interaction=interaction)

    @disnake.ui.button(label="🔁", style=disnake.ButtonStyle.primary)
    async def loop_song(
        self, button: disnake.Button, interaction: disnake.ApplicationCommandInteraction
    ):
        """
        A button that loops the song.
        """

        await self.controller.loop(interaction=interaction)

    @disnake.ui.button(label="Show", style=disnake.ButtonStyle.green)
    async def show_queue(
        self, button: disnake.Button, interaction: disnake.ApplicationCommandInteraction
    ):
        """
        A button that shows the queue.
        """
        await self.controller.show_queue(interaction=interaction)

    @disnake.ui.button(label="Lyrics", style=disnake.ButtonStyle.blurple)
    async def show_lyrics(
        self, button: disnake.Button, interaction: disnake.ApplicationCommandInteraction
    ):
        """
        A button that shows the lyrics.
        """
        await self.controller.show_lyrics(interaction=interaction)

    @disnake.ui.button(label="Shuffle", style=disnake.ButtonStyle.primary)
    async def shuffle_queue(
        self, button: disnake.Button, interaction: disnake.ApplicationCommandInteraction
    ):
        """
        A button that shuffles the queue.
        """
        await self.controller.shuffle(interaction=interaction)

    @disnake.ui.button(label="Stop", style=disnake.ButtonStyle.red)
    async def stop_song(
        self, button: disnake.Button, interaction: disnake.ApplicationCommandInteraction
    ):
        """
        A button that stops the song.
        """
        await self.controller.stop(interaction=interaction)

    async def on_error(
        self,
        error: Exception,
        item: Item,
        interaction: disnake.MessageInteraction,
    ) -> None:
        """
        This method is called when an error occurs.
        """
        if interaction.response.is_done():
            safe_send = interaction.followup.send
        else:
            safe_send = interaction.response.send_message

        # ignore all other exception types, but print them to stderr

        error_msg = "".join(
            traceback.format_exception(type(error), error, error.__traceback__)
        )
        paste = await self.bot.mystbin_client.post(error_msg, syntax="py")
        url = paste.url

        await safe_send(
            embed=disnake.Embed(
                description=f"{self.bot.icons['redtick']} `An error has occurred while "
                f"executing {interaction.data.name} command. The error has been generated on "
                f"mystbin. "
                f"Please report this to {', '.join([str(owner) for owner in await self.bot.get_owners])}`",
                colour=disnake.Colour.random(),
            ),
            view=ErrorView(url=url),
        )

        print(
            f"Ignoring exception in command {interaction.data.name}: ",
            file=sys.stderr,
        )
        traceback.print_exception(
            type(error), error, error.__traceback__, file=sys.stderr
        )


class MenuController:
    def __init__(
        self,
        player: Player,
        interaction: disnake.ApplicationCommandInteraction,
        bot: Bot,
    ):
        self.player = player
        self.interaction = interaction
        self.bot = bot

    def is_author(self, interaction: disnake.ApplicationCommandInteraction):
        """
        Check whether the user is the command invoker / interaction.author`.

        Parameters
        ----------
        interaction : disnake.ApplicationCommandInteraction
            The Interaction of the command.

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

    def vote_check(self, interaction: disnake.ApplicationCommandInteraction):
        """
        Returns required votes based on amount of members in a channel.

        Parameters
        ----------
        interaction : disnake.ApplicationCommandInteraction
            The Interaction of the command.

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

    async def pause(self, interaction: disnake.ApplicationCommandInteraction):
        """
        This method will pause the music player, if it is playing a track.

        Parameters
        ----------
        interaction: disnake.ApplicationCommandInteraction
            The Interaction of the command.
        """
        player: Player = self.bot.wavelink.get_player(
            guild_id=interaction.guild.id, cls=Player, context=interaction
        )

        if player.is_paused:
            return await interaction.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['redtick']} `The player is already paused.`",
                    colour=disnake.Colour.random(),
                ),
                ephemeral=True,
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
                delete_after=10,
            )

    async def resume(self, interaction: disnake.ApplicationCommandInteraction):
        """
        This method will resume the music player if it is paused.

        Parameters
        ----------
        interaction : disnake.ApplicationCommandInteraction
            The Interaction of the command.
        """
        player: Player = self.bot.wavelink.get_player(
            guild_id=interaction.guild.id, cls=Player, context=interaction
        )

        if not player.is_paused:
            return await interaction.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['redtick']} `The player is not paused.`",
                    colour=disnake.Colour.random(),
                ),
                delete_after=10,
                ephemeral=True,
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
                f"{interaction.author} has voted to resume the song.", delete_after=10
            )

    async def skip(self, interaction: disnake.ApplicationCommandInteraction):
        """
        This method will skip to the next song in queue. You need to have songs in queue to skip.
        The DJ of the song, can skip it without voting, else the members listening to the track, need to vote to skip.

        Parameters
        ----------
        interaction: disnake.ApplicationCommandInteraction
            The Interaction of the command.
        """
        player: Player = self.bot.wavelink.get_player(
            guild_id=interaction.guild.id, cls=Player, context=interaction
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
                delete_after=10,
            )

    async def show_lyrics(self, interaction: disnake.ApplicationCommandInteraction):
        """
        This method will show the lyrics of the current playing song or the name of the song you want lyrics
        for, if you explicitly specify it.

        Parameters
        ----------
        interaction : disnake.ApplicationCommandInteraction
            The Interaction of the command.
        """
        player: Player = self.bot.wavelink.get_player(
            guild_id=interaction.guild.id, cls=Player, context=interaction
        )

        name = player.now.title

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
                ephemeral=True,
            )

        data = await resp.json()
        await interaction.response.send_message(content="Generating lyrics....")

        lyrics = data["lyrics"]
        content = WrapText(lyrics, length=1000)
        pag = LyricsPaginator(
            lyrics=content, ctx=interaction, thumbnail=player.current.thumbnail
        )
        await pag.start()

    async def shuffle(self, interaction: disnake.ApplicationCommandInteraction):
        """
        This method will shuffle the entire queue of the current music player instance.
        You need at least 3 songs or more in queue in order to shuffle properly.

         Parameters
        ----------
        interaction: disnake.ApplicationCommandInteraction
            The Interaction of the command.
        """
        player: Player = self.bot.wavelink.get_player(
            guild_id=interaction.guild.id, cls=Player, context=interaction
        )

        if player.queue.qsize() < 3:
            return await interaction.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['info']} Add more songs before shuffling.",
                    color=disnake.Colour.random(),
                ),
                ephemeral=True,
            )

        if self.is_author(interaction):
            await interaction.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['info']} `{player.dj}` has shuffled the queue.",
                    color=disnake.Colour.random(),
                ),
                ephemeral=True,
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
                ),
                delete_after=10,
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

    async def show_queue(self, interaction: disnake.ApplicationCommandInteraction):
        """
        This method will show all the songs that queued in the music player. It has pagination,
        so it's easy for you to browse.

        Parameters
        ----------
        interaction : disnake.ApplicationCommandInteraction
            The Interaction of the command.`
        """
        player: Player = self.bot.wavelink.get_player(
            guild_id=interaction.guild.id, cls=Player, context=interaction
        )

        if player.queue.qsize() == 0:
            return await interaction.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['info']} There are no more songs "
                    f"in the queue.",
                    colour=disnake.Colour.random(),
                ),
                ephemeral=True,
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

    async def loop(self, interaction: disnake.ApplicationCommandInteraction):
        """
        A method that will loop your specific music track and keep playing it repeatedly.

        Parameters
        ----------
        interaction: disnake.ApplicationCommandInteraction
            The Interaction of the command.
        """
        player: Player = self.bot.wavelink.get_player(
            guild_id=interaction.guild.id, cls=Player, context=interaction
        )

        if not self.is_author(interaction):
            return await interaction.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['info']} Only the `{player.dj}` can loop this song.",
                    color=disnake.Colour.random(),
                ),
                ephemeral=True,
            )

        if player.loop is False:
            await interaction.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['greentick']} Looped the current track.",
                    color=disnake.Colour.random(),
                ),
                delete_after=14,
            )
            player.loop = True
            return

        if player.loop is True:
            await interaction.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['greentick']} Unlooped the current track.",
                    color=disnake.Colour.random(),
                ),
                delete_after=14,
            )
            player.loop = False
            return

    async def stop(self, interaction: disnake.ApplicationCommandInteraction):
        """
        This method will stop the currently playing song and the music player and only the DJ can use this command.

        Parameters
        ----------
        interaction: disnake.ApplicationCommandInteraction
            The Interaction of the command.
        """
        player: Player = self.bot.wavelink.get_player(
            guild_id=interaction.guild.id, cls=Player, context=interaction
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
                ), delete_after=10,
            )
            await player.teardown()
        else:
            await interaction.response.send_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['info']} `{interaction.author}` has voted to stop the song.",
                    color=disnake.Colour.random(),
                ), delete_after=10
            )
