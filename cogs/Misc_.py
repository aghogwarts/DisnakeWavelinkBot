#  -*- coding: utf-8 -*-
from youtubesearchpython.__future__ import ChannelsSearch, VideosSearch

import difflib
import pathlib
import re
import sys
import time
import traceback
import typing

import disnake
import humanize
import youtube_dl as ydl
from disnake.ext import commands
from disnake.ext.commands import InvokableSlashCommand, Param

from core.MusicBot import Bot
from utils.helpers import BotInformationView, ErrorView, executor_function
from utils.paginators import SimpleEmbedPages
from wavelink import Player


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


class Misc(commands.Cog):
    """
    Miscellaneous commands.
    """

    def __init__(self, bot: typing.Union[commands.Bot, commands.AutoShardedBot, Bot]):
        self.bot = bot

    async def cog_slash_command_error(
            self, ctx: disnake.ApplicationCommandInteraction, error: Exception
    ) -> None:
        """
        Cog wide error handler.

        This is called when a command fails to execute.

        Parameters
        ----------
        ctx : disnake.ApplicationCommandInteraction
            The Interaction of the command.

        error : Exception
            The error that was raised.
        """
        if ctx.response.is_done():
            safe_send = ctx.followup.send
        else:
            safe_send = ctx.response.send_message

        # ignore all other exception types, but print them to stderr

        error_msg = "".join(
            traceback.format_exception(type(error), error, error.__traceback__)
        )
        paste = await self.bot.mystbin_client.post(error_msg, syntax="py")
        url = paste.url

        await safe_send(
            embed=disnake.Embed(
                description=f"{self.bot.icons['redtick']} `An error has occurred while "
                            f"executing {ctx.application_command.name} command. The error has been generated on "
                            f"mystbin. "
                            f"Please report this to {', '.join([str(owner) for owner in await self.bot.get_owners])}`",
                colour=disnake.Colour.random(),
            ),
            view=ErrorView(url=url),
        )

        print(
            f"Ignoring exception in command {ctx.application_command}: ",
            file=sys.stderr,
        )
        traceback.print_exception(
            type(error), error, error.__traceback__, file=sys.stderr
        )

    @commands.slash_command(description="Shows information about the bot.")
    async def info(self, ctx: disnake.ApplicationCommandInteraction):
        """
        This command shows information about the bot.

        Parameters
        ----------
        ctx : disnake.ApplicationCommandInteraction
            The Interaction of the command.

        Examples
        --------
        `/info`
        """
        player: Player = self.bot.wavelink.get_player(
            guild_id=ctx.guild.id, cls=Player, context=ctx
        )

        permissions = disnake.Permissions(294410120513)
        github_url = "https://github.com/KortaPo/DisnakeWavelinkBot"
        url = disnake.utils.oauth_url(
            client_id=self.bot.user.id,
            scopes=["bot", "applications.commands"],
            permissions=permissions,
        )
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
                    letters_ = sum(len(f.open().read()) for f in p.rglob("*.py"))
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
            return files, classes, funcs, comments, lines, letters_

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
       {self.bot.icons['arrow']} **Commands**: 
       `{len([cmd for cmd in list(self.bot.walk_commands()) if not cmd.hidden])}`""",
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
       {self.bot.icons['arrow']} **Name**: `{', '.join([owner.name for owner in await self.bot.get_owners])}`
       {self.bot.icons['arrow']} **ID**: `{', '.join([str(owner.id) for owner in await self.bot.get_owners])}`""",
            inline=True,
        )
        em.add_field(
            name="Developers",
            value=f"""
       {self.bot.icons['arrow']} `KortaPo#8459`      
       """,
            inline=True,
        )
        em.add_field(
            name="Invite",
            value=f"[Click here to Invite {self.bot.user.name}]({url})",
            inline=True,
        )
        em.add_field(
            name="Source Code",
            value=f"[Click here to view the source code of {self.bot.user.name}]({github_url})",
            inline=True,
        )
        em.set_thumbnail(url=self.bot.user.avatar.url)
        em.set_footer(
            text=f"Python {version[0]}.{version[1]}.{version[2]} • disnake {disnake.__version__}"
        )
        await ctx.response.send_message(
            embed=em,
            view=BotInformationView(bot=self.bot, player=player, interaction=ctx),
        )

    @commands.slash_command(
        description="Shows you spotify song information of an user's spotify rich presence"
    )
    async def spotify(
            self,
            ctx: disnake.ApplicationCommandInteraction,
            user: disnake.Member = Param(description="member to search for"),
    ):
        """
        This command shows you spotify song information of a user's spotify rich presence,
        if the user is playing a song.

        Parameters
        ----------
        ctx : disnake.ApplicationCommandInteraction
            The Interaction of the command.

        user : disnake.Member
            The member to query.

        Examples
        --------
        `/spotify user: @Member`
        """

        activities = user.activities
        try:
            act = [
                activity
                for activity in activities
                if isinstance(activity, disnake.Spotify)
            ][0]
        except IndexError:
            return await ctx.channel.send("No spotify was detected")
        start = humanize.naturaltime(disnake.utils.utcnow() - act.created_at)
        print(start)
        name = act.title
        art = " ".join(act.artists)
        album = act.album
        duration = round(((act.end - act.start).total_seconds() / 60), 2)
        min_sec = time.strftime(
            "%M:%S", time.gmtime((act.end - act.start).total_seconds())
        )
        current = round(((disnake.utils.utcnow() - act.start).total_seconds() / 60), 2)
        min_sec_current = time.strftime(
            "%M:%S", time.gmtime((disnake.utils.utcnow() - act.start).total_seconds())
        )
        embed = disnake.Embed(color=ctx.guild.me.color)
        embed.set_author(
            name=user.display_name,
            icon_url="https://netsbar.com/wp-content/uploads/2018/10/Spotify_Icon.png",
        )
        embed.description = f"Listening To  [**{name}**] (https://open.spotify.com/track/{act.track_id})"
        embed.add_field(name="Artist", value=art, inline=True)
        embed.add_field(name="Album", value=album, inline=True)
        embed.set_thumbnail(url=act.album_cover_url)
        embed.add_field(name="Started Listening", value=start, inline=True)
        percent = int((current / duration) * 25)
        perbar = f"`{min_sec_current}`| {(percent - 1) * '─'}⚪️{(25 - percent) * '─'} | `{min_sec}`"
        embed.add_field(name="Progress", value=perbar)
        await ctx.response.send_message(embed=embed)

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

    @commands.slash_command(name="help", description="Shows help about bot commands.")
    async def show_help(
            self,
            ctx: disnake.ApplicationCommandInteraction,
            slash_command: str = Param(description="Command to get help for."),
    ):
        """
        This command shows help about bot commands.

        Parameters
        ----------
        ctx : disnake.ApplicationCommandInteraction
            The Interaction of the command.
        slash_command : str
            The command to get help for.

        Examples
        --------
        `/help slash_command: info`
        """
        slash_commands = [command for command in self.bot.all_slash_commands]
        if slash_command in slash_commands:
            await ctx.response.send_message("Gathering Information...")

            command: InvokableSlashCommand = self.bot.get_slash_command(slash_command)
            if len(command.children) > 0:
                embeds = []
                for key, value in command.children.items():
                    try:
                        examples = (
                            value.callback.__doc__.replace("\n", "")
                                .split("Examples")[1]
                                .replace("--------", "")
                        )
                    except AttributeError:
                        continue

                    embed = disnake.Embed(
                        colour=disnake.Colour.random(),
                        title=f"Help for {slash_command} {key}",
                        timestamp=disnake.utils.utcnow(),
                    ).set_footer(
                        text=f"Requested by {ctx.author.display_name}",
                        icon_url=ctx.author.display_avatar.url,
                    )
                    embed.add_field(
                        name="Usage",
                        value=f"`/{slash_command} {key} {', '.join([option.name for option in value.option.options])}`",
                    )
                    embed.add_field(
                        name="Description",
                        value=f"`{value.docstring['description']}`",
                        inline=False,
                    )
                    embed.add_field(name="Examples", value=f"{examples}", inline=False)
                    embeds.append(embed)

                pag = SimpleEmbedPages(entries=embeds, ctx=ctx)
                await pag.start()

            else:
                pass
            try:
                examples = (
                    command.callback.__doc__.replace("\n", "")
                        .split("Examples")[1]
                        .replace("--------", "")
                )
            except AttributeError:
                pass

            embed = disnake.Embed(
                colour=disnake.Colour.random(),
                title=f"Help for {slash_command}",
                timestamp=disnake.utils.utcnow(),
            ).set_footer(
                text=f"Requested by {ctx.author.display_name}",
                icon_url=ctx.author.display_avatar.url,
            )
            embed.add_field(
                name="Usage",
                value=f"`/{command.name} {', '.join([option.name for option in command.options])}`",
            )
            embed.add_field(
                name="Description",
                value=f"`{command.docstring['description']}`",
                inline=False,
            )
            embed.add_field(name="Examples", value=f"{examples}", inline=False)

            return await ctx.edit_original_message(
                content=f":question: **{slash_command}**", embed=embed
            )
        else:
            return await ctx.response.send_message(
                f"{self.bot.icons['redtick']} This command does not exists.",
                ephemeral=True,
            )

    @show_help.autocomplete(option_name="slash_command")
    async def command_auto(
            self, _: disnake.ApplicationCommandInteraction, user_input: str
    ):
        """
        This command autocompletes the command to get help for.

        Parameters
        ----------
        _ : disnake.ApplicationCommandInteraction
            The Interaction of the command.

        user_input : str
            The user input.

        Returns
        -------
        list
            The list of commands matching the user input.
        """
        commands = [command.lower() for command in self.bot.all_slash_commands]
        selected_commands = difflib.get_close_matches(user_input.lower(), commands)
        return selected_commands


def setup(bot):
    bot.add_cog(Misc(bot))
