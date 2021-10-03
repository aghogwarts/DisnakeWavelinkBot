import json
from traceback import print_exc
from typing import Optional

import disnake
from aiohttp import ClientSession
from disnake import Intents, AllowedMentions
from disnake.ext import commands

from bot_utils.Help_ import HelpCommand


class Bot(commands.AutoShardedBot):
    """A subclass of `commands.AutoShardedBot` with additional features."""

    with open("./bot_utils/config.json") as f:
        icons = json.load(f)
    icons = icons["ICONS"]  # creating custom bot attributes

    def __init__(self, *args, **kwargs):
        intents = Intents.all()
        intents.dm_messages = False  # Disabling this Intent will make the Bot not receive DM message events

        super().__init__(
            command_prefix="?",
            intents=intents,
            allowed_mentions=AllowedMentions(everyone=False, users=False, roles=False),
            help_command=HelpCommand(),
            case_insensitive=True,
            reload=True,  # This Kwarg Enables Cog watchdog, Hot reloading of cogs.
            activity=disnake.Game("Music Bot written in Disnake"),
            *args,
            **kwargs,
        )

        self.session: Optional[ClientSession] = None
        with open("./bot_utils/config.json") as f:
            data = json.load(f)

    def load_cogs(self, *exts) -> None:
        """Load a set of extensions."""

        for ext in exts:
            try:
                self.load_extension(ext)
            except Exception as e:
                print_exc()

    async def login(self, *args, **kwargs) -> None:
        """Create the ClientSession before logging in."""

        self.session = ClientSession()

        await super().login(*args, **kwargs)

    async def on_ready(self):
        print(f"----------Bot Initialization.-------------\n"
              f"Bot name: {self.user.name}\n"
              f"Bot ID: {self.user.id}\n"
              f"Total Guilds: {len(self.guilds)}\n"
              f"Total Users: {len(self.users)}\n"
              f"------------------------------------------")

    async def on_disconnect(self):
        await self.session.close()