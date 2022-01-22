#  -*- coding: utf-8 -*-
import asyncio
import datetime
import functools
import pathlib
import sys
import time
import typing
from enum import Enum

import disnake
import humanize
import yaml
from disnake.ext import commands
from loguru import logger

import wavelink
from utils.paginators import RichPager, ViewPages
from wavelink import Player


class BotInformation:
    def __init__(
        self,
        bot,
        player: wavelink.Player,
    ):
        self.bot = bot
        self.player = player

    async def get_lavalink_info(
        self, ctx: disnake.ApplicationCommandInteraction
    ) -> disnake.Embed:
        player: Player = self.bot.wavelink.get_player(
            guild_id=ctx.guild.id, cls=Player, context=ctx
        )
        node = player.node

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
        ).set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.avatar.url)
        return embed

    async def get_bot_info(self, _: disnake.ApplicationCommandInteraction):

        version = sys.version_info
        em = disnake.Embed(color=disnake.Colour.random())

        # File Stats
        def line_count():
            """
            Counts the number of lines in the codebase.

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
        Gets the uptime of the bot.

        Parameters
        ----------
        ctx: disnake.ApplicationCommandInteraction
            The Interaction of the command.

        Returns
        -------
        str
            The uptime of the bot.
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
        Gets the latency of the bot.

        Parameters
        ----------
        ctx: disnake.ApplicationCommandInteraction
            The Interaction of the command.

        Returns
        -------
        str
            The latency of the bot.
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
    Used to get the configurations from a yaml file.
    """

    def __init__(self, file: str = "./config/config.yaml"):
        with open(file, encoding="utf-8") as f:
            self.data = yaml.load(f, Loader=yaml.FullLoader)

    @property
    def prefix(self) -> typing.Optional[str]:
        """
        Gets the prefix of the bot.

        Returns
        -------
        str
            The prefix of the bot.
        """
        prefix = self.data["Bot"]["prefix"]
        if prefix is None:
            logger.error("Prefix is not set in the config.yaml file.")
            exit(code=1)

        return prefix

    @property
    def token(self) -> typing.Optional[str]:
        """
        Gets the token of the bot.

        Returns
        -------
        str
            The token of the bot.
        """
        token = self.data["Bot"]["token"]
        if token == "":
            logger.error("No token found in config.yaml")
            exit(code=1)
        return token

    @property
    def owners(self) -> typing.Optional[typing.Set[int]]:
        """
        Gets the owners of the bot.

        Returns
        -------
        list
            The owners of the bot.
        """
        owners = self.data["Bot"]["owners"]
        if not owners:
            logger.error(
                "No owners found in config.yaml, if you are the bot owner, "
                "please add yourself to the owners list."
            )
            exit(code=1)
        return set(owners)


class LyricsPaginator(ViewPages):
    """
    A custom paginator for lyrics.
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
    An enum used to determine the search service to use. Useful, if you want search songs with a specific service.
    """

    ytsearch = "ytsearch"
    ytmsearch = "ytmsearch"
    scsearch = "scsearch"

    def __str__(self):
        return self.value


class BotInformationView(disnake.ui.View):
    def __init__(
        self,
        interaction: disnake.ApplicationCommandInteraction,
        bot: typing.Union[commands.Bot, commands.AutoShardedBot],
        player: Player,
    ):
        super().__init__(timeout=20)
        self.interaction = interaction
        self.bot = bot
        self.player = player
        self.BotInformation = BotInformation(bot=bot, player=player)

    @disnake.ui.button(
        label="Lavalink Information", emoji="📜", style=disnake.ButtonStyle.green
    )
    async def lavalink_info(
        self,
        _: disnake.ui.Button,
        interaction: disnake.ApplicationCommandInteraction,
    ):
        """
        Shows the lavalink information.

        Parameters
        ----------
        _ : disnake.ui.Button
            The button that was pressed.

        interaction : disnake.ApplicationCommandInteraction
            The interaction of the command.
        """
        await interaction.response.defer()
        await self.interaction.edit_original_message(
            embed=await self.BotInformation.get_lavalink_info(ctx=self.interaction)
        )

    @disnake.ui.button(label="Latency", emoji="🤖", style=disnake.ButtonStyle.blurple)
    async def latency(
        self,
        _: disnake.ui.Button,
        interaction: disnake.ApplicationCommandInteraction,
    ):
        """
        Shows the latency of the bot.

        Parameters
        ----------
        _ : disnake.ui.Button
            The button that was pressed.

        interaction : disnake.ApplicationCommandInteraction
            The interaction of the command.
        """
        await interaction.response.defer()
        embed = await self.BotInformation.get_latency(ctx=self.interaction)
        await self.interaction.edit_original_message(embed=embed)

    @disnake.ui.button(label="Uptime", emoji="⏳", style=disnake.ButtonStyle.blurple)
    async def uptime(
        self,
        _: disnake.ui.Button,
        interaction: disnake.ApplicationCommandInteraction,
    ):
        """

        Parameters
        ----------
        _ : disnake.ui.Button
            The button that was pressed.

        interaction : disnake.ApplicationCommandInteraction
            The interaction of the command.
        """
        await interaction.response.defer()
        await self.interaction.edit_original_message(
            embed=await self.BotInformation.get_uptime(ctx=self.interaction)
        )

    @disnake.ui.button(label="Quit", style=disnake.ButtonStyle.red, emoji="❌")
    async def quit(
        self,
        _: disnake.ui.Button,
        interaction: disnake.ApplicationCommandInteraction,
    ):
        """

        Parameters
        ----------
        _ : disnake.ui.Button
            The button that was pressed.

        interaction : disnake.ApplicationCommandInteraction
            The interaction of the command.
        """
        await interaction.response.defer()
        await self.interaction.delete_original_message()

    async def on_timeout(self) -> None:
        for button in self.children:
            button.disabled = True
        try:
            await self.interaction.edit_original_message(view=self)
        except Exception as e:
            logger.error(f"Failed to edit message: {e}")
            return


def executor_function(sync_function: typing.Callable):
    """A decorator that wraps a sync function in an executor, changing it into an async function.

    This allows processing functions to be wrapped and used immediately as an async function.

    Examples
    ---------

    Pushing processing with the Python Imaging Library into an executor:

    .. code-block:: python3

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
