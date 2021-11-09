import threading
import subprocess
from loguru import logger

bash_command = "cd Lavalink && java -jar Lavalink.jar"  # command that needs to be run on shell.

program = 'java'  # checking that if Java is installed on the host system or not.


def run_lavalink_process():
    """A function that runs the Lavalink server"""
    process = subprocess.run(['which', program], capture_output=True, text=True)
    if process.returncode == 0:
        print(
            f'The program "{program}" is installed. Lavalink can run.')  # checking if Java is installed on the host 
        # system. 
        print(f'The location of the binary is: {process.stdout}')

        output = subprocess.run(bash_command, shell=True, capture_output=True, text=True)  # running the command on
        # shell.
        # and yes this command is dangerous.
        logger.info("Lavalink has started.")
        print(output.stdout)
        logger.info("Lavalink is running.")
    else:
        print(f'Sorry program {program} is not installed in your system. Please install it in order to run our Jar '
              f'application.')
        print(process.stderr)
        logger.info("Lavalink is not running.")
        return


def lavalink_alive():
    target = threading.Thread(target=run_lavalink_process)
    target.start()
