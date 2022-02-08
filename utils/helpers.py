#  -*- coding: utf-8 -*-
import asyncio
import datetime
import functools
import pathlib
import random
import sys
import time
import typing
from enum import Enum
from random import Random

import disnake
import humanize
import yaml
from disnake.ext import commands
from loguru import logger

import wavelink
from utils.paginators import RichPager, ViewPages
from wavelink import Player


class BotInformation:
    """
    This class is a helper class that has various methods that return various kinds of information about the bot
    and the environment it is running in.
    This class is paired with `BotInformationView` so that the information can be accesssed with interaction components.

    """

    def __init__(
        self,
        bot,
        player: wavelink.Player,
    ):
        self.bot = bot
        self.player = player

    async def get_lavalink_info(
        self, interaction: disnake.ApplicationCommandInteraction
    ) -> disnake.Embed:
        """
        This method returns a `disnake.Embed` containing information about the connected Lavalink node instance.

        Parameters
        ----------
        interaction: disnake.ApplicationCommandInteraction
            The Interaction of the command.

        Returns
        -------
        `disnake.Embed`
            An embed containing information about the Lavalink node connected to the bot.
        """
        player: Player = self.bot.wavelink.get_player(
            guild_id=interaction.guild.id, cls=Player, context=interaction
        )
        node: wavelink.Node = player.node

        used = humanize.naturalsize(node.stats.memory_used)
        total = humanize.naturalsize(node.stats.memory_allocated)
        free = humanize.naturalsize(node.stats.memory_free)
        cpu = node.stats.cpu_cores

        fmt = (
            f"**WaveLink:** `{wavelink.__version__}`\n\n"
            f"Connected to `{len(self.bot.wavelink.nodes)}` nodes.\n"
            f"Best available Node `{self.bot.wavelink.get_best_node().__repr__()}`\n"
            f"`{len(self.bot.wavelink.players)}` players are distributed on nodes.\n"
            f"`{node.stats.players}` players are distributed on server.\n"
            f"`{node.stats.playing_players}` players are playing on server.\n\n"
            f"Server Memory: `{used}/{total}` | `({free} free)`\n"
            f"Server CPU: `{cpu}`\n\n"
            f"Server Uptime: `{humanize.precisedelta(datetime.timedelta(milliseconds=node.stats.uptime))}`"
        )
        embed = disnake.Embed(
            description=fmt,
            colour=disnake.Colour.random(),
            title="Lavalink Information",
        ).set_footer(
            text=f"Requested by {interaction.author}",
            icon_url=interaction.author.display_avatar.url,
        )
        return embed

    async def get_bot_info(
        self, interaction: disnake.ApplicationCommandInteraction
    ) -> disnake.Embed:
        """
        A method that returns a `disnake.Embed` containing various information about the bot.

        Parameters
        ----------
        interaction: disnake.ApplicationCommandInteraction
            The Interaction of the command.

        Returns
        -------
        `disnake.Embed`
            An embed containing information about the bot.
        """
        # TODO: This method has issues returning data, when the bot is run on a specific host, heroku,
        #  I am not sure why, maybe its not with heroku but my code, so I have to investigate this.
        #  If you have any ideas, please make a PR and let me know.

        version = sys.version_info
        em = disnake.Embed(color=disnake.Colour.random())

        # File Stats
        def line_count() -> typing.Tuple[int, int, int, int, int, int]:
            """
            This function returns the number of lines in the bot's source code.

            Returns
            -------
            tuple[int, int, int, int, int, int]
                The number of lines in the codebase.
            """
            files = classes = funcs = comments = lines = letters = 0
            p = pathlib.Path("./")
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

        (
            files,
            classes,
            funcs,
            comments,
            lines,
            letters,
        ) = await self.bot.loop.run_in_executor(None, line_count)
        #
        em.add_field(
            name="Bot",
            value=f"""
               {self.bot.icons['arrow']} **Guilds**: `{len(self.bot.guilds)}`
               {self.bot.icons['arrow']} **Users**: `{len(self.bot.users)}`
               {self.bot.icons['arrow']} **Commands**: `{len([cmd for cmd in list(self.bot.walk_commands())
                                                              if not cmd.hidden])}`""",
            inline=True,
        )
        em.add_field(
            name="File Statistics",
            value=f"""
               {self.bot.icons['arrow']} **Letters**: `{letters}`
               {self.bot.icons['arrow']} **Files**: `{files}`
               {self.bot.icons['arrow']} **Lines**: `{lines}`
               {self.bot.icons['arrow']} **Functions**: `{funcs}`""",
            inline=True,
        )
        em.add_field(
            name="Bot Owner",
            value=f"""
               {self.bot.icons['arrow']} **Name**: `{self.bot.owner}`
               {self.bot.icons['arrow']} **ID**: `{self.bot.owner.id}`
               """,
            inline=True,
        )
        em.add_field(
            name="Developers",
            value=f"""
               {self.bot.icons['arrow']} `KortaPo#8459`       
               """,
            inline=True,
        )
        em.set_thumbnail(url=self.bot.user.display_avatar.url)
        em.set_footer(
            text=f"Python {version[0]}.{version[1]}.{version[2]} • disnake {disnake.__version__}"
        )
        return em

    async def get_uptime(
        self, ctx: disnake.ApplicationCommandInteraction
    ) -> disnake.Embed:
        """
        This method returns an embed containing information about the bot's uptime.

        Parameters
        ----------
        ctx: disnake.ApplicationCommandInteraction
            The Interaction of the command.

        Returns
        -------
        `disnake.Embed`
            An embed containing information about the uptime of the bot.
        """
        uptime = disnake.utils.utcnow() - self.bot.start_time
        time_data = humanize.precisedelta(uptime)
        embed = disnake.Embed(
            title="Uptime", description=time_data, colour=disnake.Colour.random()
        ).set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.avatar.url)
        return embed

    async def get_latency(
        self, ctx: disnake.ApplicationCommandInteraction
    ) -> disnake.Embed:
        """
        This method returns an embed containing information about the bot's latency.

        Parameters
        ----------
        ctx: disnake.ApplicationCommandInteraction
            The Interaction of the command.

        Returns
        -------
        `disnake.Embed`
            An embed containing information about the latency of the bot.
        """
        times = []
        counter = 0
        embed = disnake.Embed(colour=disnake.Colour.random())
        for _ in range(3):
            counter += 1
            start = time.perf_counter()
            await ctx.edit_original_message(
                content=f"Trying Ping {('.' * counter)} {counter}/3"
            )
            end = time.perf_counter()
            speed = round((end - start) * 1000)
            times.append(speed)
            if speed < 160:
                embed.add_field(
                    name=f"Ping {counter}:", value=f"🟢 | {speed}ms", inline=True
                )
            elif speed > 170:
                embed.add_field(
                    name=f"Ping {counter}:", value=f"🟡 | {speed}ms", inline=True
                )
            else:
                embed.add_field(
                    name=f"Ping {counter}:", value=f"🔴 | {speed}ms", inline=True
                )

        embed.add_field(name="Bot Latency", value=f"{round(self.bot.latency * 1000)}ms")
        embed.add_field(
            name="Normal Speed",
            value=f"{round((round(sum(times)) + round(self.bot.latency * 1000)) / 4)}ms",
        )

        embed.set_footer(text=f"Total estimated elapsed time: {round(sum(times))}ms")
        embed.set_author(name=ctx.me.display_name, icon_url=ctx.me.display_avatar.url)
        return embed


class Config:
    """
    A helper class containing methods for the configuration of the bot.
    This class is only useful for this codebase as the methods are hardcoded.
    """

    def __init__(self):
        self.bot_config_file_path = "./config/config.yaml"
        self.Lavalink_config_file_path = "./Lavalink/application.yml"
        with open(self.bot_config_file_path, encoding="utf-8") as f:
            self.data = yaml.load(f, Loader=yaml.FullLoader)
        with open(self.Lavalink_config_file_path, encoding="utf-8") as f:
            self.Lavalink_data = yaml.load(f, Loader=yaml.FullLoader)
        

    @property
    def prefix(self) -> typing.Optional[str]:
        """
        This property returns the prefix of the bot from the config file.
        """
        prefix = self.data["Bot"]["prefix"]
        if prefix is None:
            logger.error("Prefix is not set in the config.yaml file.")
            exit(code=1)

        return prefix

    @property
    def token(self) -> typing.Optional[str]:
        """
        This property returns the token of the bot from the config file.
        """
        token = self.data["Bot"]["token"]
        if token is None:
            logger.error("No token found in config.yaml")
            exit(code=1)
        return token

    @property
    def owners(self) -> typing.Optional[typing.Set[int]]:
        """
        This method returns a list of owner ID (integer) that is set in the config file.

        Returns
        -------
        list
            The owner IDs of the bot.
        """
        owners = self.data["Bot"]["owners"]
        if not owners:
            logger.error(
                "No owners found in config.yaml, if you are the bot owner, "
                "please add yourself to the owners list."
            )
            exit(code=1)
        return set(owners)

    @property
    def lavalink_host(self) -> typing.Optional[str]:
        """
        This method returns the host of the Lavalink server.
        """
        host = self.Lavalink_data["server"]["address"]
        if host is None:
            logger.error("No Lavalink address found in application.yml")
            sys.exit(1)
        return host

    @property
    def lavalink_port(self) -> typing.Optional[int]:
        """
        This method returns the port of the Lavalink server.
        """
        port = self.Lavalink_data["server"]["port"]
        if port is None:
            logger.error("No Lavalink port found in application.yml")
            sys.exit(1)
        return int(port)

    @property
    def lavalink_password(self) -> typing.Optional[str]:
        """
        This method returns the password of the Lavalink server.
        """
        password = self.Lavalink_data["lavalink"]["server"]["password"]
        if password is None:
            logger.error("No Lavalink password found in application.yml")
            sys.exit(1)
        return password


class LyricsPaginator(ViewPages):
    """
    A custom paginator for lyrics that subclasses the ViewPages.
    """

    def __init__(
        self, ctx: disnake.ApplicationCommandInteraction, lyrics: list, thumbnail: str
    ):
        super().__init__(ctx=ctx, source=RichPager(lyrics, per_page=10))
        self.embed = (
            disnake.Embed(
                title="Lyrics",
                colour=disnake.Colour.random(),
            )
            .set_footer(
                text=f"Requested by {ctx.author}",
                icon_url=ctx.author.display_avatar.url,
            )
            .set_thumbnail(url=thumbnail)
        )


class SearchService(str, Enum):
    """
    An Enum used to determine the search service to use. Useful, if you want search songs with a specific service.
    """

    ytsearch = "ytsearch"
    ytmsearch = "ytmsearch"
    scsearch = "scsearch"
    spsearch = "spsearch"
    amsearch = "amsearch"

    def __str__(self):
        return self.value


ServiceOptions = commands.option_enum(
    {
        "youtube": "youtube",
        "soundcloud": "soundcloud",
        "youtubemusic": "youtubemusic",
        "spotify": "spotify",
        "applemusic": "applemusic",
    }
)


class BotInformationView(disnake.ui.View):
    def __init__(
        self,
        interaction: disnake.ApplicationCommandInteraction,
        bot,
        player: Player,
    ):
        super().__init__(timeout=30)
        self.interaction = interaction
        self.bot = bot
        self.player = player
        self.BotInformation = BotInformation(bot=bot, player=player)
        self.is_message_deleted = False

    @disnake.ui.button(
        label="Lavalink Information", emoji="📜", style=disnake.ButtonStyle.green
    )
    async def lavalink_info(
        self,
        button: disnake.ui.Button,
        interaction: disnake.ApplicationCommandInteraction,
    ):
        """
        This button shows the lavalink information by calling the BotInformation.lavalink_info method.

        Parameters
        ----------
        button : disnake.ui.Button
            The button that was pressed. (Unused)

        interaction : disnake.ApplicationCommandInteraction
            The interaction of the command.
        """
        await interaction.response.defer()
        await self.interaction.edit_original_message(
            embed=await self.BotInformation.get_lavalink_info(
                interaction=self.interaction
            )
        )

    @disnake.ui.button(label="Latency", emoji="🤖", style=disnake.ButtonStyle.blurple)
    async def latency(
        self,
        button: disnake.ui.Button,
        interaction: disnake.ApplicationCommandInteraction,
    ):
        """
        This button shows the latency of the bot by calling the BotInformation.latency method.

        Parameters
        ----------
        button : disnake.ui.Button
            The button that was pressed. This argument is not used.

        interaction : disnake.ApplicationCommandInteraction
            The interaction of the command.
        """
        try:
            await interaction.response.defer()
        except disnake.errors.NotFound:
            pass
        embed = await self.BotInformation.get_latency(ctx=self.interaction)
        await self.interaction.edit_original_message(embed=embed)

    @disnake.ui.button(label="Uptime", emoji="⏳", style=disnake.ButtonStyle.blurple)
    async def uptime(
        self,
        button: disnake.ui.Button,
        interaction: disnake.ApplicationCommandInteraction,
    ):
        """
        This button shows the uptime of the bot by calling the BotInformation.uptime method.

        Parameters
        ----------
        button : disnake.ui.Button
            The button that was pressed. This argument is not used.

        interaction : disnake.ApplicationCommandInteraction
            The interaction of the command.
        """
        try:
            await interaction.response.defer()
        except disnake.errors.NotFound:
            pass
        await self.interaction.edit_original_message(
            embed=await self.BotInformation.get_uptime(ctx=self.interaction)
        )

    @disnake.ui.button(label="Quit", style=disnake.ButtonStyle.red, emoji="❌")
    async def quit(
        self,
        button: disnake.ui.Button,
        interaction: disnake.ApplicationCommandInteraction,
    ):
        """
        This button quits the view.

        Parameters
        ----------
        button : disnake.ui.Button
            The button that was pressed. This argument is not used.

        interaction : disnake.ApplicationCommandInteraction
            The interaction of the command.
        """
        try:
            await interaction.response.defer()
        except disnake.errors.NotFound:
            pass
        self.is_message_deleted = True
        await self.interaction.delete_original_message()

    async def on_timeout(self) -> None:
        if self.is_message_deleted:
            return

        for button in self.children:
            button.disabled = True

        try:
            await self.interaction.edit_original_message(view=self)
        except Exception as e:
            logger.error(f"Failed to edit message: {e}")
            return


def executor_function(sync_function: typing.Callable):
    #  Taken from Jishaku https://github.com/Gorialis/jishaku/blob/master/jishaku/functools.py#L19
    """
    A decorator that wraps a sync function in an executor, changing it into an async function.

    This allows processing functions to be wrapped and used immediately as an async function.

    Examples
    ---------

    Pushing processing with the Python Imaging Library into an executor:

    from io import BytesIO
    from PIL import Image

    @executor_function
    def color_processing(color: disnake.Color):
        with Image.new('RGB', (64, 64), color.to_rgb()) as im:
            buff = BytesIO()
            im.save(buff, 'png')

        buff.seek(0)
        return buff

    @bot.command()
    async def color(ctx: commands.Context, color: disnake.Color):
        color = color or ctx.author.color
        buff = await color_processing(color=color)

        await ctx.channel.send(file=disnake.File(fp=buff, filename='color.png'))
    """

    @functools.wraps(sync_function)
    async def sync_wrapper(*args, **kwargs):
        """
        Asynchronous function that wraps a sync function with an executor.
        """

        loop = asyncio.get_event_loop()
        internal_function = functools.partial(sync_function, *args, **kwargs)
        return await loop.run_in_executor(None, internal_function)

    return sync_wrapper


class ErrorView(disnake.ui.View):
    """
    A view that displays an error message.
    """

    def __init__(self, url: str):
        self.url = url
        super().__init__()

        self.add_item(item=disnake.ui.Button(label="View Error", url=url, emoji="🤖"))

