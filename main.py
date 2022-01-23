#  -*- coding: utf-8 -*-
import sys
import time

from loguru import logger

from core.MusicBot import Bot
from utils.helpers import Config
from utils.process import lavalink_alive

if __name__ == "__main__":

    bot = Bot()
    config = Config()
    bot.load_cogs("cogs")
    logger.info("All cogs have been successfully loaded", __name="Music Bot")
    logger.info("Starting Lavalink.....", __name="Music Bot")
    lavalink_alive()  # running Lavalink. It's important to run this before the bot starts.
    try:
        time.sleep(30)  # Wait for lavalink to start

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
