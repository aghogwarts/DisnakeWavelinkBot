import yaml
from loguru import logger
from MusicBot import Bot
from bot_utils.Lavalink_run import lavalink_alive
import time
from yaml import load

with open("config.yaml") as f:
    config = load(f, Loader=yaml.Loader)

if __name__ == "__main__":

    bot = Bot()
    bot.load_cogs("cogs")
    logger.info("All cogs have been successfully loaded", __name="Music Bot")
    lavalink_alive()
    try:
        time.sleep(14)  # Wait for lavalink to start

        bot.run(config["token"][0], reconnect=True)
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
            bot.session.close()  # Closing the ClientSession
            logger.info("Closing Aiohttp ClientSession...", __name="Music Bot")
            bot.clear()  # clearing the cache
            logger.info("Clearing Bot Cache", __name="Music Bot")
            exit(0)
        except AttributeError:
            logger.info("Gracefully stopping the program....", __name="Music Bot")
            exit(0)
