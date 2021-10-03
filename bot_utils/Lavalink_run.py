import os
import threading


def run():
    os.system("cd Lavalink && java -jar Lavalink.jar")


def lavalink_alive():
    target = threading.Thread(target=run)
    target.start()
