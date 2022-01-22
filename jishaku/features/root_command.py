# -*- coding: utf-8 -*-

"""
jishaku.features.root_command
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The jishaku root command.

:copyright: (c) 2021 Devon (Gorialis) R
:license: MIT, see LICENSE for more details.

"""

import math
import sys
import typing

import disnake
from disnake.ext import commands

from jishaku.features.baseclass import Feature
from jishaku.flags import Flags
from jishaku.modules import package_version
from jishaku.paginators import PaginatorInterface

try:
    import psutil
except ImportError:
    psutil = None


def natural_size(size_in_bytes: int):
    """
    Converts a number of bytes to an appropriately-scaled unit
    E.g.:
        1024 -> 1.00 KiB
        12345678 -> 11.77 MiB
    """
    units = ("B", "KiB", "MiB", "GiB", "TiB", "PiB", "EiB", "ZiB", "YiB")

    power = int(math.log(size_in_bytes, 1024))

    return f"{size_in_bytes / (1024 ** power):.2f} {units[power]}"


class RootCommand(Feature):
    """
    Feature containing the root jsk command
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.jsk.hidden = Flags.HIDE

    @Feature.Command(
        name="jishaku", aliases=["jsk"], invoke_without_command=True, ignore_extra=False
    )
    async def jsk(self, ctx: commands.Context):  # pylint: disable=too-many-branches
        """
        The Jishaku debug and diagnostic commands.

        This command on its own gives a status brief.
        All other functionality is within its subcommands.
        """
        embed = (
            disnake.Embed(title="Technical Information", color=disnake.Colour.random())
            .set_footer(
                text=f"Requested by {ctx.author}",
                icon_url=ctx.author.display_avatar.url,
            )
            .set_thumbnail(url=ctx.bot.user.display_avatar.url)
        )
        embed.add_field(
            name="Version",
            value=f"Jishaku `v2.3.1`.\ndisnake `v{package_version('disnake')}`.\nPython `{sys.version}` on "
            f"`{sys.platform.replace(' ', '')}`.\nModule was "
            f"loaded <t:{self.load_time.timestamp():.0f}:R>, cog was "
            f"loaded <t:{self.start_time.timestamp():.0f}:R>.",
        )

        # detect if [procinfo] feature is installed
        if psutil:
            try:
                proc = psutil.Process()

                with proc.oneshot():
                    try:
                        mem = proc.memory_full_info()
                        embed.add_field(
                            name="Memory Usage",
                            value=f"Using `{natural_size(mem.rss)}` physical memory and "
                            f"`{natural_size(mem.vms)}` virtual memory, "
                            f"`{natural_size(mem.uss)}` of which unique to this process.",
                            inline=False,
                        )
                    except psutil.AccessDenied:
                        pass

                    try:
                        name = proc.name()
                        pid = proc.pid
                        thread_count = proc.num_threads()
                        embed.add_field(
                            name="Process and Threads",
                            value=f"Running on PID `{pid}` (`{name}`) with `{thread_count}` thread(s).",
                            inline=False,
                        )
                    except psutil.AccessDenied:
                        pass

            except psutil.AccessDenied:
                embed.add_field(
                    name="Unable to access process information",
                    value="You do not have permission to access process information.",
                )
        cache_summary = (
            f"{len(self.bot.guilds)} guild(s) and {len(self.bot.users)} user(s)"
        )

        # Show shard settings to summary
        if isinstance(self.bot, disnake.AutoShardedClient):
            if len(self.bot.shards) > 20:
                embed.add_field(
                    name="Shard Information",
                    value=f"This bot is automatically sharded ({len(self.bot.shards)} shards of {self.bot.shard_count})"
                    f" and can see {cache_summary}.",
                    inline=False,
                )
            else:
                shard_ids = ", ".join(str(i) for i in self.bot.shards.keys())
                embed.add_field(
                    name="Shard Information",
                    value=f"This bot is automatically sharded ({len(self.bot.shards)} shards of {self.bot.shard_count})"
                    f" and can see {cache_summary}.",
                    inline=False,
                )
        elif self.bot.shard_count:
            embed.add_field(
                name="Shard Information",
                value=f"This bot is manually sharded ({self.bot.shard_id} shards of {self.bot.shard_count})"
                f" and can see {cache_summary}.",
                inline=False,
            )
        else:
            embed.add_field(
                name="\u200b",
                value=f"This bot is not sharded and can see `{cache_summary}`.",
            )

        # pylint: disable=protected-access
        if self.bot._connection.max_messages:
            embed.add_field(
                name="Message Cache",
                value=f"`{self.bot._connection.max_messages}` messages are cached.",
                inline=False,
            )
            message_cache = (
                f"Message cache capped at {self.bot._connection.max_messages}"
            )
        else:
            message_cache = "Message cache is disabled"
            embed.add_field(name="\u200b", value=message_cache, inline=False)

        if disnake.version_info >= (1, 5, 0):
            presence_intent = f"`Presence Intent` is {'enabled' if self.bot.intents.presences else 'disabled'}."
            members_intent = f"`Members Intent` is {'enabled' if self.bot.intents.members else 'disabled'}."
            message_intent = f"`Message Inten` is {'enabled' if self.bot.intents.messages else 'disabled'}."
            guild_intent = f"`Guild Intent` is {'enabled' if self.bot.intents.guilds else 'disabled'}."

            embed.add_field(
                name="Intents",
                value=f"{presence_intent}\n{members_intent}\n{message_intent}\n{guild_intent}",
                inline=False,
            )
        else:
            guild_subscriptions = f"Guild subscriptions are {'enabled' if self.bot._connection.guild_subscriptions else 'disabled'}."
            dm_subscriptions = f"DM subscriptions are {'enabled' if self.bot._connection.dm_subscriptions else 'disabled'}."
            embed.add_field(
                name="Intents",
                value=f"{guild_subscriptions}\n{dm_subscriptions}",
                inline=False,
            )

        # pylint: enable=protected-access

        # Show websocket latency in milliseconds
        embed.add_field(
            name="Websocket Latency",
            value=f"`{self.bot.latency * 1000:.2f}` ms",
            inline=False,
        )

        await ctx.channel.send(embed=embed)

    # pylint: disable=no-member
    @Feature.Command(parent="jsk", name="hide")
    async def jsk_hide(self, ctx: commands.Context):
        """
        Hides Jishaku from the help command.
        """

        if self.jsk.hidden:
            return await ctx.channel.send("Jishaku is already hidden.")

        self.jsk.hidden = True
        await ctx.channel.send("Jishaku is now hidden.")

    @Feature.Command(parent="jsk", name="show")
    async def jsk_show(self, ctx: commands.Context):
        """
        Shows Jishaku in the help command.
        """

        if not self.jsk.hidden:
            return await ctx.channel.send("Jishaku is already visible.")

        self.jsk.hidden = False
        await ctx.channel.send("Jishaku is now visible.")

    # pylint: enable=no-member

    @Feature.Command(parent="jsk", name="tasks")
    async def jsk_tasks(self, ctx: commands.Context):
        """
        Shows the currently running jishaku tasks.
        """

        if not self.tasks:
            return await ctx.channel.send("No currently running tasks.")

        paginator = commands.Paginator(max_size=1985)

        for task in self.tasks:
            paginator.add_line(
                f"{task.index}: `{task.ctx.command.qualified_name}`, invoked at "
                f"{task.ctx.message.created_at.strftime('%Y-%m-%d %H:%M:%S')} UTC"
            )

        interface = PaginatorInterface(ctx.bot, paginator, owner=ctx.author)
        return await interface.send_to(ctx)

    @Feature.Command(parent="jsk", name="cancel")
    async def jsk_cancel(self, ctx: commands.Context, *, index: typing.Union[int, str]):
        """
        Cancels a task with the given index.

        If the index passed is -1, will cancel the last task instead.
        """

        if not self.tasks:
            return await ctx.channel.send("No tasks to cancel.")

        if index == "~":
            task_count = len(self.tasks)

            for task in self.tasks:
                task.task.cancel()

            self.tasks.clear()

            return await ctx.channel.send(f"Cancelled {task_count} tasks.")

        if isinstance(index, str):
            raise commands.BadArgument('Literal for "index" not recognized.')

        if index == -1:
            task = self.tasks.pop()
        else:
            task = disnake.utils.get(self.tasks, index=index)
            if task:
                self.tasks.remove(task)
            else:
                return await ctx.channel.send("Unknown task.")

        task.task.cancel()
        return await ctx.channel.send(
            f"Cancelled task {task.index}: `{task.ctx.command.qualified_name}`,"
            f" invoked at {task.ctx.message.created_at.strftime('%Y-%m-%d %H:%M:%S')} UTC"
        )
