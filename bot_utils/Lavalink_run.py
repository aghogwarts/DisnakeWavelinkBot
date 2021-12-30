#  -*- coding: utf-8 -*-


import threading
import subprocess
from loguru import logger

bash_command = (
    "cd Lavalink && java -jar Lavalink.jar"  # command that needs to be run on shell.
)

BaseProgram = "java"  # checking that if Java is installed on the host's system or not.


def run_lavalink_process():
    """
    A function that runs the Lavalink server.

    Returns
    -------
    None
    """
    process = subprocess.run(["which", BaseProgram], capture_output=True, text=True)
    if process.returncode == 0:
        logger.success(
            f'The program "{BaseProgram}" is installed. Lavalink can be run.'
        )  # checking if Java is installed on the host
        # system.
        logger.info(f"The location of {BaseProgram} is: {process.stdout}")

        output = subprocess.run(
            bash_command, shell=True, capture_output=True, text=True
        )  # running the command on
        # shell.
        # and yes using shell kwarg can be dangerous.
        if output.returncode == 0:
            logger.success("Lavalink is running.")
        else:
            logger.error(f"Lavalink is not running. Error: {output.stdout}")
    else:
        logger.error(
            f"Sorry, {BaseProgram} is not installed in your system. Please install it in order to run our Lavalink."
        )
        print(process.stdout)


def lavalink_alive():
    """
    A function that creates a thread that runs the Lavalink server.

    Returns
    -------
    None
    """
    target = threading.Thread(target=run_lavalink_process)
    target.start()
