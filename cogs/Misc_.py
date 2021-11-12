import datetime
import difflib
import pathlib
import sys
import time
import traceback

import disnake
import humanize
from disnake.ext import commands
import psutil
from disnake.ext.commands import Param
import wavelink
from wavelink import Player


class Misc(commands.Cog):
    """Miscellaneous commands."""

    def __init__(self, bot):
        self.bot = bot

    async def cog_slash_command_error(self, ctx: disnake.ApplicationCommandInteraction, error: Exception) -> None:
        """Cog wide error handler."""
        if ctx.response.is_done():
            safe_send = ctx.followup.send
        else:
            safe_send = ctx.response.send_message

        # ignore all other exception types, but print them to stderr

        error_msg = "".join(traceback.format_exception(type(error), error, error.__traceback__))
        await safe_send(embed=disnake.Embed(
            description=f"**Error invoked by: {str(ctx.author)}**\nCommand: {ctx.application_command.name}\nError: "
                        f"```py\n{error_msg}```",
            color=disnake.Colour.random()))

        print(f"Ignoring exception in command {ctx.application_command}: ", file=sys.stderr)
        traceback.print_exception(type(error), error, error.__traceback__, file=sys.stderr)

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

    @commands.slash_command(description="Shows you the bot's uptime.")
    async def uptime(self, ctx: disnake.ApplicationCommandInteraction):
        await ctx.response.send_message("Gathering Information...")
        embed = disnake.Embed(colour=disnake.Colour.random())
        embed.set_author(name=ctx.me.display_name, icon_url=ctx.me.avatar.url)
        embed.add_field(name="Uptime", value=f"{humanize.naturaltime(disnake.utils.utcnow() - self.bot.start_time)}")
        await ctx.edit_original_message(content=":clock1: **Uptime**", embed=embed)

    @commands.slash_command(name="help", description="Shows help about bot commands.")
    async def show_help(self, ctx: disnake.ApplicationCommandInteraction,
                        slash_command: str = Param(description="Command to get help for.")):
        slash_commands = [command for command in self.bot.all_slash_commands]
        if slash_command in slash_commands:
            await ctx.response.send_message("Gathering Information...")

            command = self.bot.get_slash_command(slash_command)
            embed = disnake.Embed(colour=disnake.Colour.random(),
                                  title=f"Help for {slash_command}",
                                  description=f"Usage: **/{command.name}{command.kwargs}**\n"
                                              f"Description:\n`{command.description}`",
                                  timestamp=disnake.utils.utcnow()).set_footer(
                text=f"Requested by {ctx.author.display_name}",
                icon_url=ctx.author.avatar.url)
            return await ctx.edit_original_message(content=f":question: **{slash_command}**", embed=embed)
        else:
            return await ctx.response.send_message(f"{self.bot.icons['redtick']} This command does not exists.",
                                                   ephemeral=True)

    @show_help.autocomplete(option_name="slash_command")
    async def command_auto(self, ctx: disnake.ApplicationCommandInteraction, user_input: str):
        commands = [command for command in self.bot.all_slash_commands]
        selected_commands = difflib.get_close_matches(user_input, commands, n=5)
        return selected_commands


def setup(bot):
    bot.add_cog(Misc(bot))
