# Music Bot

An example music bot that is written in Disnake [Maintained discord.py Fork] 

## Disnake 
Disnake is a maintained and updated fork of `discord.py`.
```
Disnake Github Repo -> https://github.com/EQUENOS/disnake
```

## Installation

Use the package manager [pip](https://pip.pypa.io/en/stable/) to install the libraries from ``requirements.txt`` file.

```bash
pip install -r requirements.txt
```

## Note
This music bot uses Lavalink to play music. Lavalink is a Java based program.
You will need JDK 8 or JDK 13 to be able to run Lavalink properly.
Wavelink has been rewritten. (Imports changed from discord to disnake)

You will need `python 3.8` or above to run this program.

The entire music bot operates on slash commands.

## What is Lavalink and how this music bot works??
Lavalink is a standalone audio streaming node and an API that is based on `Lavaplayer`. Unlike youtube_dl or ffmpeg which downloads tracks and plays, Lavalink loads the tracks and streams the audio
through a websocket. 

Wavelink is an API wrapper that is written for `python` to abstract away all the complexities of
Lavalink and make it easy for us to load and play tracks.

If you want know more about Lavalink, vist this repo:
https://github.com/freyacodes/Lavalink


## How to run this.
Go to the website - https://discord.com/developers/applications.

Create your own bot account.

Enable Privileged Intents - Member Intents /Presence Intents.

Enable ``applications/commands`` scope to make sure your bot can have slash commands.

Go to the ``config.yaml`` file and Enter your ``Discord Bot Token``.

You need to python installed on your system in order to run the program.

Then run the ``main.py`` file.

```bash
  python3 main.py
```

Run it on your terminal.

If you don't have python installed in your system, 
Please refer to https://python.org/downloads to download python.
Make sure you have installed version 3.8 or above of python.

If all the steps are correctly followed, the bot should be up and running.

Enjoy :).

## I am beginner in programming, and I want to use this code.
I will be frank here.
You need to have basic programming knowledge in python and Disnake.

Here is what the author of Disnake thinks you should know before beginning:


How much Python do I need to know?

disnake is ultimately a complicated Python library for beginners. There are many concepts in there that can trip a beginner up and could be confusing. The design of the library is to be easy to use -- however the target audience for the library is not complete beginners of Python.

With that being said, beginners tend to use this library quite liberally anyway and while I appreciate the endeavour and tenacity it should be noted that asking for help here does take up the valuable time of volunteers. As a result certain knowledge is recomended before trying disnake:

- The difference between instances and class attributes.
    - e.g. guild.name vs disnake.Guild.name or any variation of these.
- How to use data structures in the language.
    - dict/tuple/list/str/...
- How to solve NameError or SyntaxError exceptions.
- How to read and understand tracebacks.

This list is not exhaustive

 If these concepts are confusing -- please feel free to complete a smaller and simpler project first before diving into the complexities that is asynchronous programming in Python.
 (Taken from a tag.)


## Credits
If you are using this, or any part of it, please feel free to give some credits :)
Thanks.