import os
import pkgutil
from difflib import get_close_matches
from io import BytesIO
import disnake
from disnake.ext import commands
from disnake.ext.commands import Param


async def command_autocomp(inter, user_input):
    # This func will suggest options to complete the string argument
    all_items = ["enable", "disable", "reload", "remove"]
    return [item for item in all_items if user_input.lower() in item]


async def bot_commands_autocomp(inter: disnake.Interaction, user_input: str = "s"):
    total_commands = [item.name for item in inter.bot.message_commands if user_input.lower() in item]
    commands_return = get_close_matches(user_input, total_commands)
    return commands_return


async def cog_autocomp(inter, user_input):
    cog_names = []
    for pkg in pkgutil.iter_modules(['cogs']):
        cog_names.append(pkg.name)
    return [item for item in cog_names if user_input.lower() in item]


class Owner(commands.Cog, name="Developer"):
    """Commands specifically developer for Bot developers."""

    def __init__(self, bot):
        self.bot = bot

    async def cog_command_error(self, ctx: disnake.ApplicationCommandInteraction, error: Exception) -> None:
        """Handles errors raised by commands in the cog."""
        if isinstance(error, commands.NotOwner):
            await ctx.response.send_message(embed=disnake.Embed(description="You are not the owner of this bot.",
                                                                color=disnake.Colour.random()))

    @commands.slash_command(description="Commands that handle Bot commands and Cogs")
    @commands.is_owner()
    async def botconfig(self, ctx: disnake.ApplicationCommandInteraction):
        pass

    @botconfig.sub_command(description="Cog manager")
    @commands.is_owner()
    async def cog(self, ctx: disnake.ApplicationCommandInteraction, action: str = Param(autocomplete=command_autocomp),
                  cog: str = Param(autocomplete=cog_autocomp)):

        if action.lower() == 'disable':

            try:
                self.bot.unload_extension(f"cogs.{cog}")
            except Exception:
                return await ctx.response.send_message(embed=disnake.Embed(
                    description=f"Cog **{cog}** is not loaded.", color=disnake.Colour.random()), ephemeral=True)

            await ctx.response.send_message(embed=disnake.Embed(
                description=f"Cog **{cog}** has stopped running.", color=disnake.Colour.random()), ephemeral=True)

        elif action.lower() == 'enable':

            try:
                self.bot.load_extension(f"cogs.{cog}")
            except Exception as error:
                with BytesIO() as file:
                    trace = __import__('traceback').format_exception(etype=type(error), value=error,
                                                                     tb=error.__traceback__)
                    file.write(bytes(''.join(trace).encode('ascii')))
                    file.seek(0)

                    error_file = disnake.File(fp=file, filename='error.log')

                return await ctx.response.send_message(f"{self.bot.icons['info']} This cog has an error located in it. "
                                                       , file=error_file, ephemeral=True)

            await ctx.response.send_message(f"Cog **{cog}** is now running.", ephemeral=True)

        elif action.lower() == 'reload':

            try:
                self.bot.reload_extension(f"cogs.{cog}")
            except Exception as error:
                with BytesIO() as file:
                    trace = __import__('traceback').format_exception(etype=type(error), value=error,
                                                                     tb=error.__traceback__)
                    file.write(bytes(''.join(trace).encode('ascii')))
                    file.seek(0)

                    error_file = disnake.File(fp=file, filename='error.log')

                return await ctx.response.send_message(f"{self.bot.icons['info']} This cog has an error located in it. "
                                                       , file=error_file, ephemeral=True)

            await ctx.response.send_message(f"Cog **{cog}** has been reloaded.", ephemeral=True)

    @botconfig.sub_command(aliases=["cgi"])
    async def coginfo(self, ctx: disnake.ApplicationCommandInteraction):
        loaded_cogs = []
        for cog in self.bot.extensions.keys():
            cog_name = cog.split('.')
            try:
                loaded_cogs.append(f"{cog_name[1] + '.py'}")
            except IndexError:
                continue
        print(loaded_cogs)
        unloaded = []
        cogs = 0
        for file in os.listdir('./cogs'):
            if file != '__pycache__':
                cogs += 1
                if file not in loaded_cogs:
                    unloaded.append(file)

        embed = disnake.Embed(title='Loaded Cogs & Commands:', colour=disnake.Colour.random())
        embed.add_field(name='Cogs:',
                        value=f"**Total:** `{cogs}`\n**Loaded:** `{len(loaded_cogs)}`"
                              f"\n**Unloaded:** `{', '.join(unloaded) or 'None!'}`")
        enabled, disabled, _commands = 0, 0, []
        for cmd in self.bot.commands:
            if not cmd.enabled:
                disabled += 1
                _commands.append(cmd.name)
            else:
                enabled += 1
        embed.add_field(name='Commands:',
                        value=f"**Total:** `{len(self.bot.commands)}`\n**Enabled:** `{enabled}`\n**Disabled:** `{disabled}`",
                        inline=False)

        await ctx.response.send_message(embed=embed, ephemeral=True)

    @commands.slash_command(aliases=["clean"], description="Purges bot messages.")
    @commands.is_owner()
    async def cleanup(self, ctx: disnake.ApplicationCommandInteraction,
                      amount: int = Param(description="Amount of messages", default=10)):
        deleted = []
        messages = []
        async with ctx.channel.typing():
            async for m in ctx.channel.history(limit=amount):
                messages.append(m)
                if m.author == self.bot.user:
                    try:
                        await m.delete()
                    except Exception:
                        pass
                    else:
                        deleted.append(m)
        await ctx.response.send_message(f"Successfully deleted {len(deleted)}/{len(messages)} messages",
                                        ephemeral=True)

    @botconfig.sub_command(description="Command config setup.")
    @commands.is_owner()
    async def command(self, ctx: disnake.ApplicationCommandInteraction,
                      action: str = Param(autocomplete=command_autocomp),
                      command: str = Param(autocomplete=bot_commands_autocomp)):
        bot_commands = {cmd.name.lower(): cmd for cmd in self.bot.commands}
        command = bot_commands.get(command.lower())
        if not command:
            return await ctx.response.send_message(embed=disnake.Embed(
                description=f"`{command.name}` does not exist", color=disnake.Colour.random()), ephemeral=True)

        if action.lower() == 'remove':
            self.bot.remove_command(command.name)
            return await ctx.response.send_message(embed=disnake.Embed(
                description=f"Command **{command.name}** has been removed from the bot.",
                color=disnake.Colour.random()),
                ephemeral=True)

        elif action.lower() == 'disable':
            if not command.enabled:
                return await ctx.response.send_message(embed=disnake.Embed(description=f"Command **{command.name}** "
                                                                                       f"is already disabled.",
                                                                           color=disnake.Colour.random()),
                                                       ephemeral=True)
            command.enabled = False
            return await ctx.response.send_message(embed=disnake.Embed(description=f"Command **{command.name}** "
                                                                                   f"has been disabled.",
                                                                       color=disnake.Colour.random()), ephemeral=True)

        elif action.lower() == 'enable':
            if command.enabled:
                return await ctx.response.send_message(embed=disnake.Embed(description=f"Command **{command.name}** "
                                                                                       f"is already enabled.",
                                                                           color=disnake.Colour.random()),
                                                       ephemeral=True)
            command.enabled = True
            return await ctx.response.send_message(embed=disnake.Embed(description=f"Command **{command.name}** "
                                                                                   f"has been enabled.",
                                                                       color=disnake.Colour.random()), ephemeral=True)

    @commands.slash_command(name="setstatus", description="Sets the bot's status.")
    @commands.is_owner()
    async def status(self, ctx: disnake.Interaction):
        pass

    @status.sub_command(description="Set Streaming Status.")
    async def streaming(self, ctx: disnake.Interaction, url: str = Param(description="Stream url"), 
                        game: str = Param(description="Game name")):
        game = (game
                .replace("{users}", str(len(self.bot.users)))
                .replace("{guilds}", str(len(self.bot.guilds))))
        await self.bot.change_presence(
            activity=disnake.Streaming(name=str(game), url=f'https://www.twitch.tv/{url.lower()}'))
        await ctx.response.send_message(embed=disnake.Embed(description=f"Streaming status set to **{game}**",
                                                            colour=disnake.Colour.random()), ephemeral=True)

    @status.sub_command(description="Set Playing Status.")
    async def playing(self, ctx: disnake.Interaction, game: str = Param(description="Game")):

        game = (game
                .replace("{users}", str(len(self.bot.users)))
                .replace("{guilds}", str(len(self.bot.guilds))))
        await self.bot.change_presence(activity=disnake.Game(name=game))
        await ctx.response.send_message(embed=disnake.Embed(description=f"Playing status set to **{game}**",
                                                            colour=disnake.Colour.random()), ephmeral=True)

    @status.sub_command(description="Set Watching Status.")
    async def watching(self, ctx: disnake.Interaction, game: str):

        game = (game
                .replace("{users}", str(len(self.bot.users)))
                .replace("{guilds}", str(len(self.bot.guilds))))
        await self.bot.change_presence(activity=disnake.Activity(name=f"{game}", type=3))
        await ctx.response.send_message(embed=disnake.Embed(description=f"Watching status set to **{game}**",
                                                            colour=disnake.Colour.random()), ephemeral=True)

    @status.sub_command(description="Set Listening Status.")
    async def listening(self, ctx: disnake.Interaction, game: str):

        game = (game
                .replace("{users}", str(len(self.bot.users)))
                .replace("{guilds}", str(len(self.bot.guilds))))
        await self.bot.change_presence(activity=disnake.Activity(name=f"{game}", type=2))
        await ctx.response.send_message(embed=disnake.Embed(description=f"Listening status set to **{game}**",
                                                            colour=disnake.Colour.random()), ephemeral=True)

    @status.sub_command(description="Set Competing Status.")
    async def competing(self, ctx: disnake.Interaction, game: str):

        game = (game
                .replace("{users}", str(len(self.bot.users)))
                .replace("{guilds}", str(len(self.bot.guilds))))
        await self.bot.change_presence(activity=disnake.Activity(name=f"{game}", type=5))
        await ctx.response.send_message(embed=disnake.Embed(description=f"Competing status set to **{game}**",
                                                            colour=disnake.Colour.random()), ephemeral=True)

    @status.sub_command(description="Set Original Bot Status.")
    async def reset(self, ctx: disnake.Interaction):

        await self.bot.change_presence(activity=disnake.Game(
            f"{len(self.bot.guilds)} guilds & {len(self.bot.users)} users"))
        await ctx.response.send_message(embed=disnake.Embed(description=f"Bot status resetted",
                                                            colour=disnake.Colour.random()), ephemeral=True)


def setup(bot):
    bot.add_cog(Owner(bot))
