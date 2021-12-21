#  -*- coding: utf-8 -*-


from loguru import logger
from MusicBot import Bot
from bot_utils.Lavalink_run import lavalink_alive
import time
from bot_utils.Helpers_ import Config

if __name__ == "__main__":

    bot = Bot()
    config = Config()
    bot.load_cogs("cogs")
    logger.info("All cogs have been successfully loaded", __name="Music Bot")
    lavalink_alive()  # running Lavalink. It's important to run this before the bot starts.
    try:
        time.sleep(14)  # Wait for lavalink to start

        bot.run(config.token, reconnect=True)
    except KeyboardInterrupt:
        try:
            bot.session.close()  # Closing the ClientSession
            logger.info("Shutting down...", __name="Music Bot")
            exit(0)
        except AttributeError:
            logger.info("Exiting Program gracefully.", __name="Music Bot")
            exit(0)

    except SystemExit:
        try:
            logger.info("Closing Aiohttp ClientSession...", __name="Music Bot")
            bot.session.close()  # Closing the ClientSession
            logger.info("Clearing Bot Cache", __name="Music Bot")
            bot.clear()  # clearing the cache
            exit(0)
        except AttributeError:
            logger.info("Gracefully stopping the program....", __name="Music Bot")
            exit(0)
