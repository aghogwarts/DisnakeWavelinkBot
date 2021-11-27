import json
import pkgutil
import traceback
import zlib
from typing import Optional, Any

import loguru
from loguru import logger
import disnake
from aiohttp import ClientSession
from disnake import Intents, AllowedMentions
from disnake.ext import commands

with open("./bot_utils/config.json") as f:
    data = json.load(f)


class Bot(commands.AutoShardedBot):
    """
    A subclass of `commands.AutoShardedBot` with additional features.
    """

    def __init__(self, *args, **kwargs):
        intents = Intents.all()
        intents.dm_messages = False  # Disabling this Intent will make the Bot not receive DM message events

        super().__init__(
            command_prefix=commands.when_mentioned_or("?"),
            intents=intents,
            allowed_mentions=AllowedMentions(everyone=False, users=False, roles=False),
            case_insensitive=True,
            sync_commands_debug=True,
            help_command=None,  # type: ignore
            sync_permissions=True,
            enable_debug_events=True,
            reload=True,  # This Kwarg Enables Cog watchdog, Hot reloading of cogs.
            *args,
            **kwargs,
        )

        self.session: Optional[ClientSession] = None
        self.config = data
        self.icons = data["ICONS"]
        self.logger = logger
        self.start_time = disnake.utils.utcnow()

    def load_cogs(self, exts) -> None:
        """
        A method that loads all the cogs in the cogs folder.

        Parameters
        ----------
        exts: `Iterable[list]`
            A list of extensions to load.

        Returns
        -------
         None
        """

        for m in pkgutil.iter_modules([exts]):
            # a much better way to load cogs
            module = f"cogs.{m.name}"
            try:
                self.load_extension(module)
                self.logger.info(f"Loaded extension '{m.name}'", __name="Music Bot")
            except Exception as e:
                traceback.format_exc(e)
        self.load_extension("jishaku")
        self.logger.info(f"Loaded extension 'jishaku'", __name="Music Bot")

    async def login(self, *args, **kwargs) -> None:
        """
        A method that logs the bot into Discord.
        Create the ClientSession before logging in.

        Parameters
        ----------
        *args
            Positional arguments.
        **kwargs
            Keyword arguments.

        Returns
        -------
        None
        """

        self.session = ClientSession()

        await super().login(*args, **kwargs)

    async def on_ready(self):
        """
        An event that triggers when the bot is connected properly to gateway and bot cache is completely loaded.

        Returns
        -------
        None
        """
        print(
            f"----------Bot Initialization.-------------\n"
            f"Bot name: {self.user.name}\n"
            f"Bot ID: {self.user.id}\n"
            f"Total Guilds: {len(self.guilds)}\n"
            f"Total Users: {len(self.users)}\n"
            f"------------------------------------------"
        )

    async def on_socket_raw_receive(self, msg):
        """
        An event that triggers when the bot receives a raw message from the gateway.
        This event replicates discord.py's 'on_socket_response' event that was removed for dpy v2.0 in disnake.

        Parameters
        ----------
        msg: `bytes`
            The raw message received from the gateway.

        Returns
        -------
        None
        """
        self._zlib = zlib.decompressobj()
        self._buffer = bytearray()
        if type(msg) is bytes:
            self._buffer.extend(msg)

            if len(msg) < 4 or msg[:-4] != b"\x00\x00\xff\xff":
                return
            try:
                msg = self._zlib.decompress(self._buffer)
            except Exception:
                self._buffer = bytearray()
                return
            msg = msg.decode("utf-8")
            self._buffer = bytearray()
        msg = disnake.utils._from_json(msg)
        self.dispatch("socket_response", msg)

    async def on_disconnect(self):
        """
        An event that triggers when the bot is disconnected from the gateway.

        Returns
        -------
        None
        """
        self.clear()  # clearing bot cache
        self.logger.info(f"Bot disconnected from gateway.", __name="Music Bot")
        await self.session.close()  # closing the ClientSession
        self.logger.info(f"ClientSession closed.", __name="Music Bot")
