import sys
import traceback

import disnake
from disnake.ext import commands


class ErrorHandler(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_slash_command_error(self, ctx: disnake.ApplicationCommandInteraction, error: Exception):
        """An event that triggers when an error is raised while responding to an interaction."""
        # if command has local error handler, return
        if hasattr(ctx.application_command, 'on_slash_error'):
            return

        # get the original exception
        error = getattr(error, 'original', error)

        if isinstance(error, commands.BotMissingPermissions):
            missing = [perm.replace('_', ' ').replace('guild', 'server').title() for perm in error.missing_permissions]
            if len(missing) > 2:
                fmt = f"**{missing[:-1]}**, and **{missing[-1]}**"

            else:
                fmt = ' and '.join(missing)
            _message = f"I need the **{fmt}** permission(s) to run this command."
            await ctx.edit_original_message(content=_message)
            return

        if isinstance(error, disnake.Forbidden):
            await ctx.edit_original_message(content="**I cannot perform this action.**")

        if isinstance(error, commands.DisabledCommand):
            await ctx.edit_original_message(content='This command has been disabled.')
            return

        if isinstance(error, commands.MissingPermissions):
            missing = [perm.replace('_', ' ').replace('guild', 'server').title() for perm in error.missing_permissions]
            if len(missing) > 2:
                fmt = f"**{missing[:-1]}**, and **{missing[-1]}**"
            else:
                fmt = ' and '.join(missing)
            _message = f"You need the **{fmt}** permission(s) to use this command."
            await ctx.edit_original_message(content=_message)
            return

        if isinstance(error, commands.NoPrivateMessage):
            try:
                await ctx.edit_original_message(content=f"{self.bot.icons['redtick']} This command cannot be used in "
                                                        f"direct messages.")
            except disnake.Forbidden:
                pass
            return

        if isinstance(error, commands.CommandError):
            await ctx.send(embed=disnake.Embed(color=disnake.Colour.random(), description=f"{error}"))
            return

        # ignore all other exception types, but print them to stderr
        else:
            error_msg = "".join(traceback.format_exception(type(error), error, error.__traceback__))
            await ctx.channel.send(embed=disnake.Embed(
                description=f"**Error invoked by: {str(ctx.author)}**\nCommand: {ctx.application_command.name}\nError: "
                            f"py\n{error_msg}",
                color=disnake.Colour.random()), delete_after=10)

            print(f"Ignoring exception in command {ctx.application_command}: ", file=sys.stderr)
            traceback.print_exception(type(error), error, error.__traceback__, file=sys.stderr)


def setup(bot):
    bot.add_cog(ErrorHandler(bot))
