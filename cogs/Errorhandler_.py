import difflib
import disnake
from disnake.ext import commands
import traceback
import sys
from jishaku.models import copy_context_with
import math


class ErrorHandler(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        # if command has local error handler, return
        if hasattr(ctx.command, 'on_error'):
            return

        # get the original exception
        error = getattr(error, 'original', error)

        if isinstance(error, commands.CommandNotFound):
            if ctx.prefix != "":
                cmd = ctx.invoked_with
                cmds = [cmd.name for cmd in self.bot.commands]
                match = difflib.get_close_matches(cmd, cmds)
                try:
                    command = self.bot.get_command(match[0])
                except IndexError:
                    command = None
                if command:
                    if not command.hidden:
                        msg = await ctx.send(f"{self.bot.icons['redtick']} `{cmd}` is not a valid command, did you "
                                             f"mean `{match[0]}`?", delete_after=5)
                        reactions = [self.bot.icons['greentick'], self.bot.icons['redtick']]
                        for reaction in reactions:
                            await msg.add_reaction(reaction)

                        reaction, user = await self.bot.wait_for("reaction_add", check=lambda reaction,
                                                                                              user: user == ctx.author and str(
                            reaction.emoji) in reactions and reaction.message == msg)
                        if str(reaction.emoji) == self.bot.icons['greentick']:
                            alt_ctx = await copy_context_with(ctx, author=ctx.author,
                                                              content=f"{ctx.prefix}{match[0]}")
                            await self.bot.invoke(alt_ctx)
                            await msg.delete()
                            return
                        elif str(reaction.emoji) == self.bot.icons['redtick']:
                            await msg.delete()
                            return
                else:
                    em = disnake.Embed(description=f"`{cmd}` is not a valid command", color=disnake.Colour.random())
                    await ctx.reply(embed=em, mention_author=False, delete_after=10)
                    return
        if isinstance(error, commands.BotMissingPermissions):
            missing = [perm.replace('_', ' ').replace('guild', 'server').title() for perm in error.missing_permissions]
            if len(missing) > 2:
                fmt = f"**{missing[:-1]}**, and **{missing[-1]}**"

            else:
                fmt = ' and '.join(missing)
            _message = f"I need the **{fmt}** permission(s) to run this command."
            await ctx.send(_message)
            return

        if isinstance(error, disnake.Forbidden):
            await ctx.send("**I cannot perform this action.**")

        if isinstance(error, commands.DisabledCommand):
            await ctx.send('This command has been disabled.')
            return

        if isinstance(error, commands.NotOwner):
            if list(error.args) != [] and len(list(error.args)) != 0:
                msg = list(error.args)[0]
                return await ctx.send(f"{self.bot.icons['redtick']} {msg}")
            await ctx.send(f"{self.bot.icons['redtick']} Only the bots owner is allowed to execute this command")

        if isinstance(error, commands.CommandOnCooldown):
            await ctx.reply(embed=disnake.Embed(title="Error",
                                                description=f"This command is on cooldown, please retry in {math.ceil(error.retry_after)} second(s)",
                                                color=disnake.Colour.random()), mention_author=False)
            return

        if isinstance(error, commands.MissingPermissions):
            missing = [perm.replace('_', ' ').replace('guild', 'server').title() for perm in error.missing_permissions]
            if len(missing) > 2:
                fmt = f"**{missing[:-1]}**, and **{missing[-1]}**"
            else:
                fmt = ' and '.join(missing)
            _message = f"You need the **{fmt}** permission(s) to use this command."
            await ctx.send(_message)
            return

        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.command.send_help()
            return

        if isinstance(error, commands.NoPrivateMessage):
            try:
                await ctx.send('This command cannot be used in direct messages.')
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
                description=f"**Error invoked by: {str(ctx.author)}**\nCommand: {ctx.command.qualified_name}\nError: "
                            f"py\n{error_msg}",
                color=disnake.Colour.random()), delete_after=10)

            print(f"Ignoring exception in command {ctx.command}: ", file=sys.stderr)
            traceback.print_exception(type(error), error, error.__traceback__, file=sys.stderr)


def setup(bot):
    bot.add_cog(ErrorHandler(bot))