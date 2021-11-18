# Music Bot

An example music bot that is written in Disnake [Maintained discord.py Fork] 

## Disnake 
Disnake is a maintained and updated fork of `discord.py`.

[Disnake Github Repo](https://github.com/EQUENOS/disnake)


## Installation

Use the package manager [pip](https://pip.pypa.io/en/stable/) to install the libraries from ``requirements.txt`` file.

```bash
pip install -r requirements.txt
```

## Note
This music bot uses Lavalink to play music. Lavalink is a Java based program.
You will need JDK 8 or JDK 13 to be able to run Lavalink properly.
Wavelink has been rewritten to support disnake.
You will need `python 3.8` or above to run this program.
The entire music bot operates on slash commands and global slash commands take up to an hour to get registered.

## What is Lavalink and how this music bot works??

Lavalink is a standalone audio streaming node written in Java that is based on `Lavaplayer`(An audio player written in Java).

Lavalink creates a  REST and websocket server where our application needs to connect to. Once connect, we need to send OPcodes
through a websocket connection.
Lavalink can be configured by using a file called ``application.yml``. It is a configuration file, where you can define port/host to open a connection and a lot of different options.

Wavelink is a powerful and robust wrapper around Lavalink that is written for `python`.

It abstracts away all the complexities of Lavalink and makes it easy for us play our favourite music tracks in it, with your discord bot application.
It supports all Lavalink features.

If you want know more about Lavalink, visit this repository:
[Click here to visit](https://github.com/freyacodes/Lavalink)

## How to run this.
1.) In a web browser, navigate to [Discord Developer Portal](https://discord.com/developers/applications):

2.) Create your own __bot account__.

3.) Enable Privileged Intents - Member Intents/Presence Intents/Message Intents. (Very Important)

4.) Enable ``applications/commands`` scope to make sure your bot can have slash commands.

5.) Copy your bot token from your bot application and then open ``config.yaml`` file and enter your ``Discord Bot Token``.

6.) Then run the ``main.py`` file in your preferred code editor/ IDE.

```bash
  python3 main.py
```

If all the steps are correctly followed, the bot should be up and running.

Enjoy :).


## Credits
If you are using this, or any part of it, please feel free to give some credits :)
Thanks.
