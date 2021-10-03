import disnake
from disnake.ext import commands
import datetime
import contextlib


class HelpMenu(disnake.ui.Select):
    def __init__(self, help, mapping, homepage, emojis):
        self.help = help
        self.mapping = mapping
        self.homepage = homepage
        self.emojis = emojis
        options = [
            disnake.SelectOption(label="Home", description="The homepage of this menu", value="Home",
                                 emoji="✅")
        ]
        for cog, commands in self.mapping.items():
            name = cog.qualified_name if cog else "No"
            description = cog.description if cog else "Commands without category"
            if not name.startswith("On"):
                option = disnake.SelectOption(label=F"{name} Category [{len(commands)}]", description=description,
                                              value=name,
                                              emoji=self.emojis.get(name) if self.emojis.get(name) else '⛔')
                options.append(option)
        super().__init__(placeholder="Choose the module you want to checkout: ", min_values=1, max_values=1,
                         options=options)

    async def callback(self, interaction: disnake.Interaction):
        for cog, commands in self.mapping.items():
            name = cog.qualified_name if cog else "No"
            description = cog.description if cog else "Commands without category"
            if self.values[0] == name:
                mbed = disnake.Embed(
                    colour=disnake.Colour.random(),
                    title=F"{self.emojis.get(name) if self.emojis.get(name) else '⛔'} {name} Category [{len(commands)}]",
                    description=description,
                    timestamp=datetime.datetime.now()
                )
                for command in commands:
                    mbed.add_field(name=self.help.get_command_signature(command), value=command.help or command.description or "No help")
                mbed.set_author(name=interaction.user, icon_url=interaction.user.avatar.url)
                await interaction.response.edit_message(embed=mbed)
            elif self.values[0] == "Home":
                try:
                    await interaction.response.edit_message(embed=self.homepage)
                except disnake.InteractionResponded:
                    pass


class HelpView(disnake.ui.View):
    def __init__(self, help, mapping, homepage, emojis):
        super().__init__()
        self.help = help
        self.mapping = mapping
        self.homepage = homepage
        self.emojis = emojis
        self.add_item(HelpMenu(self.help, self.mapping, self.homepage, self.emojis))

    async def interaction_check(self, interaction: disnake.Interaction):
        if interaction.user.id == self.help.context.author.id:
            return True

        await interaction.response.send_message(
            F"<@{interaction.user.id}> - Only <@{self.help.context.author.id}> can use that.", ephemeral=True)


class HelpCommand(commands.HelpCommand):
    def __init__(self):
        self.emojis = {
            "Developer": "⌨️",
            "Jishaku": "👀",
            "Music": "🎵"
        }
        super().__init__(
            command_attrs={
                "help": "The help command for the bot",
                "aliases": ["h", "commands"]
            }
        )

    # Help Main
    async def send_bot_help(self, mapping):
        ctx = self.context
        homepage = disnake.Embed(
            colour=disnake.Colour.random(),
            title=F"{ctx.me.display_name} Help",
            description="This is a list of all modules in the bot.\nSelect a module for more information",
            timestamp=ctx.message.created_at
        )
        homepage.set_thumbnail(url=ctx.me.avatar.url)
        homepage.set_author(name=ctx.author, icon_url=ctx.author.avatar.url)
        usable = 0
        for cog, commands in mapping.items():
            if filtered_commands := await self.filter_commands(commands, sort=True):
                amount_commands = len(filtered_commands)
                usable += amount_commands
        homepage.add_field(name="Usable:", value=usable)
        homepage.add_field(name="Arguments:",
                           value="[] means the argument is optional.\n<> means the argument is required.")
        view = HelpView(self, mapping, homepage, self.emojis)
        view.message = await ctx.send(embed=homepage, view=view)
        return

    # Help Command
    async def send_command_help(self, command):
        ctx = self.context
        signature = self.get_command_signature(command)
        embed = disnake.Embed(
            colour=disnake.Colour.random(),
            title=signature,
            description=command.help or "No help found...",
            timestamp=ctx.message.created_at
        )
        embed.set_thumbnail(url=ctx.me.avatar.url)
        embed.set_author(name=ctx.author, icon_url=ctx.author.avatar.url)
        if cog := command.cog:
            embed.add_field(name="Category",
                            value=F"{self.emojis.get(cog.qualified_name) if self.emojis.get(cog.qualified_name) else ''} `{cog.qualified_name}`")
        can_run = "No"
        with contextlib.suppress(commands.CommandError):
            if await command.can_run(self.context):
                can_run = "Yes"
        embed.add_field(name="Usable", value=f"`{can_run}`")
        if command._buckets and (cooldown := command._buckets._cooldown):
            embed.add_field(name="Cooldown", value=F"`{cooldown.rate}` per `{cooldown.per:.0f}` seconds")
        await ctx.send(embed=embed)
        return

    # Help SubCommand Error
    async def subcommand_not_found(self, command, string):
        ctx = self.context
        embed = disnake.Embed(
            colour=disnake.Colour.random(),
            title="Sub Command Not Found",
            description=F"{command} - {string}",
            timestamp=ctx.message.created_at
        )
        embed.set_author(name=ctx.author, icon_url=ctx.author.avatar.url)
        embed.set_thumbnail(url=ctx.me.avatar.url)
        await ctx.send(embed=embed)
        return

    # Help Cog
    async def send_cog_help(self, cog):
        ctx = self.context
        await ctx.send_help()
        return

    # Help Group
    async def send_group_help(self, group):
        ctx = self.context
        title = self.get_command_signature(group)
        embed = disnake.Embed(
            colour=disnake.Colour.random(),
            title=title,
            description=group.help or "No help found...",
            timestamp=ctx.message.created_at
        )
        embed.set_thumbnail(url=ctx.me.avatar.url)
        embed.set_author(name=ctx.author, icon_url=ctx.author.avatar.url)
        for command in group.commands:
            embed.add_field(name=self.get_command_signature(command), value=command.help or "No help found...")
        await ctx.send(embed=embed)
        return

    # Help Error
    async def send_error_message(self, error):
        if error is None:
            return
        ctx = self.context
        embed = disnake.Embed(
            colour=disnake.Colour.random(),
            title="Help Error",
            description=error,
            timestamp=ctx.message.created_at
        )
        embed.set_author(name=ctx.author, icon_url=ctx.author.avatar.url)
        embed.set_thumbnail(url=ctx.me.avatar.url)
        await ctx.send(embed=embed)
        return