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
    bot.load_cogs('cogs')
    logger.info("All cogs have been successfully loaded", __name="Music Bot")
    lavalink_alive()
    try:
        time.sleep(14)  # Wait for lavalink to start

        bot.run(config["token"][0],
                reconnect=True)
    except KeyboardInterrupt:
        logger.info("Shutting down...", __name="Music Bot")
