#  -*- coding: utf-8 -*-


import asyncio
import itertools
import random
import typing
import async_timeout
import disnake
import humanize
import datetime
import wavelink
from bot_utils.paginator import ViewPages, RichPager


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
            return list(itertools.islice(self._queue, item.start, item.stop, item.step))
        else:
            return self._queue[item]

    def __iter__(self):
        return self._queue.__iter__()

    def __len__(self):
        return self.qsize()

    def __repr__(self):
        return f"<Queue size: {self.qsize()}>"

    def clear(self):
        """
        A method that clears the queue.
        """
        self._queue.clear()

    def shuffle(self):
        """
        A method that shuffles the queue.
        """
        random.shuffle(self._queue)

    def remove(self, index: int):
        """
        A method that removes a track from the queue.
        """
        del self._queue[index]


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
        self.music_player = None
        self.music_player_message = None
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

        if not self.loop:

            try:
                self.waiting = True
                with async_timeout.timeout(120):
                    track = await self.queue.get()
                    self.now = track
            except asyncio.TimeoutError:
                # No music has been played for 2 minutes, cleanup and disconnect.
                return await self.teardown()
        if self.loop:
            track = self.now

        await self.play(track)
        self.waiting = False

        # Start our song menu
        await self.songmenucontroller()

    async def songmenucontroller(self) -> None:
        """
        Method which handles the song menu.
        """
        if self.updating:
            return

        self.updating = True

        if not self.music_player:
            self.music_player_message = await self.context.channel.send(
                embed=await self.make_song_embed()
            )

        elif not await self.is_menu_available():
            try:
                await self.music_player_message.delete()
            except disnake.HTTPException:
                pass

            await self.context.channel.send(embed=await self.make_song_embed())

        else:
            embed = await self.make_song_embed()
            await self.context.channel.send(content=None, embed=embed)

        self.updating = False

    @staticmethod
    def parse_duration(duration: int):
        """
        Parse a duration into a human-readable string.

        Parameters
        ----------
        duration : int
            The duration to parse.

        Returns
        -------
        str
            The parsed duration.
        """
        minutes, seconds = divmod(duration, 60)
        hours, minutes = divmod(minutes, 60)
        days, hours = divmod(hours, 24)

        duration = []
        if days > 0:
            duration.append(f"{days} days")
        if hours > 0:
            duration.append(f"{hours} hours")
        if minutes > 0:
            duration.append(f"{minutes} minutes")
        if seconds > 0:
            duration.append(f"{seconds} seconds")
        else:
            duration.append("Live Stream")

        return ", ".join(duration)

    async def make_song_embed(self) -> typing.Optional[disnake.Embed]:
        """
        Method which creates the song embed containing the information about the song.

        Returns
        -------
        typing.Optional[disnake.Embed]
            The song embed.
        """
        track: Track = self.current
        if not track:
            return

        channel = self.bot.get_channel(int(self.channel_id))
        qsize = self.queue.qsize()
        position = divmod(self.position, 60000)
        length = divmod(self.now.length, 60000)

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
                if message.id == self.music_player_message.message.id:
                    return True
        except (disnake.HTTPException, AttributeError):
            return False

        return False

    async def teardown(self):
        """
        Method which handles the teardown(clearing and disconnection) of the player.
        """
        try:
            await self.music_player_message.delete()
        except disnake.HTTPException:
            pass

        try:
            await self.destroy()
        except KeyError:
            pass

    @property
    def loop(self):
        """
        Property which returns the loop of the player.
        """
        return self._loop

    @loop.setter
    def loop(self, value: bool = False):
        """
        Property which sets the loop of the player.

        Parameters
        ----------
        value : bool
            The value to set the loop to.

        Returns
        -------

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
