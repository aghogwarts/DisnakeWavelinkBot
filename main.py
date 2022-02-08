#  -*- coding: utf-8 -*-
import asyncio
import sys
import time

import uvloop
from loguru import logger
import sys
from core.MusicBot import Bot
from utils.helpers import Config

if __name__ == "__main__":
    if sys.platform == "Linux":
        asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    else:
        pass
    bot = Bot()
    config = Config()
    bot.load_cogs("cogs")
    logger.info("All cogs have been successfully loaded", __name="Music Bot")
    logger.info("Starting Bot.....", __name="Music Bot")
    try:
        time.sleep(16)  # Wait for lavalink to start

        bot.run(config.token, reconnect=True)
    except KeyboardInterrupt:
        try:
            bot.session.close()  # Closing the ClientSession
            logger.info("Shutting down...", __name="Music Bot")
            sys.exit(0)
        except AttributeError:
            logger.info("Exiting Program gracefully.", __name="Music Bot")
            sys.exit(0)

    except SystemExit:
        try:
            logger.info("Clearing Bot Cache", __name="Music Bot")
            bot.clear()  # clearing the cache
            sys.exit(0)
        except AttributeError:
            logger.info("Gracefully stopping the program....", __name="Music Bot")
            exit(0)
