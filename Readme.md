# Welcome

An example music bot that is written in Disnake [Maintained discord.py Fork] 

## Disnake 
Disnake is a maintained and an updated fork of `discord.py`. It supports and covers everything of Discord's API.

[Disnake Github Repo](https://github.com/DisnakeDev/disnake)

## Installation
There are currently two ways to install:

Use [pip package manager](https://pip.pypa.io/en/stable/) to install the libraries from ``requirements.txt`` file.

```bash
pip install -r requirements.txt
```

If you have [Poetry package manager](https://python-poetry.org/) installed, you can install the dependencies using 
the following command.

```bash
poetry install
```
As we have included a `pyproject.toml` file, it will install the dependencies automatically.

## Bot Configuration
You can configure the bot by using the file called ``application.yml`` in the ``config`` directory.
You need to pass the bot token, prefix and the bot owner's ID. For example:
```yaml
Bot:
  prefix: "!"  # Prefix for the bot, this is required.
  token: "..." # Bot token, this is required.
  owners: 
     - 1234 # Bot owner's ID, this is required, if you do not have multiple owners, just pass your ID.
     - 1234 # Another owner's ID, if you have multiple owners.
```
You can also configure the emojis used by the bot, through the ``icons.json`` file in the ``config`` directory.
You can pass your own emojis, or use the default ones. If you are passing custom emojis, 
you need to pass the emojis in the following format:
``<:emoji_name:emoji_id>``

Lavalink configuration is also available in the ``application.yml`` file. Read # Lavalink Configuration 
section for more information.
Lavalink is already configured by default, so you shouldn't change anything.


## Note
Before starting to use this project, here are some things you should note:

**1**.) This music bot uses Lavalink to play music. As Lavalink is a Java based program, you will need JDK 8 or JDK 13 to be able to run Lavalink properly.

**2**.) Wavelink has been rewritten for this project to support the latest versions of Lavalink, and disnake.

**3**.) You will need Python version `3.8` or above to run this program, anything below version `3.8` will not work.

**4**.) The bot mostly uses slash commands for most its functionality, but it also has messages commands.

**5**.) This bot is currently only tested on Linux. So if you encounter any issues, please create an issue and report it.

**6**.) `You will need to have a spotify account to use play songs with spotify. Head over to [Spotify](https://developer.spotify.com/) to create one.`
## Installing Lavalink

Visit [Lavalink dev](https://ci.fredboat.com/buildConfiguration/Lavalink_Build?branch=refs%2Fheads%2Fdev&mode=builds&guest=1) to download the development version.

Install Lavalink.jar in the directory ``Lavalink`` and that's it.

## Spotify Support
This bot supports spotify. 
You will need to have a spotify account to use play songs with spotify. Head over to [Spotify](https://developer.spotify.com/) to create one.
You will need client ID and client secret and pass it into ``application.yml`` file.

```yaml
plugins:
  spotify:
    clientId: "Stuff here"
    clientSecret: "Stuff here"
    countryCode: "IN"
    providers:
      - "ytsearch:\"%ISRC%\""
      - "scsearch: %QUERY%"
      - "ytsearch: %QUERY%"
```

This is required for the bot to work. This bot uses [TopiSenpai's Spotify Plugin](https://github.com/Topis-Lavalink-Plugins/Spotify-Plugin).

## YouTube Age Restrictions
You can configure the bot to play YouTube videos that are age restricted, normally Lavalink is not able to play age restricted videos.
But by passing certain parameters to the ``application.yml`` file, you can configure the bot to play age restricted videos.

```yaml
youtubeConfig:
  PAPISID: "__3-Secure-PAPISID__"
  PSID: "__3-Secure-PSID__"
```

Read [YouTube Age Restriction Bypass](https://github.com/Walkyst/lavaplayer-fork/issues/18)  to know how to get these keys.


## What is Lavalink and how this music bot works??

Lavalink is a standalone audio streaming node written in Java that is based on `Lavaplayer`(An audio player written in Java).

Lavalink creates a  REST and websocket server where our application needs to connect to. Once connected, we need to send OPcodes
that Lavalink requires, through websocket that Lavalink created.

For example, if we want to play a song, we need to send the following OPcode and the neccesary data through websocket:
```json
{
    "op": "play",
    "guildId": "...",
    "track": "...",
    "startTime": "60000",
    "endTime": "120000",
    "volume": "100",
    "noReplace": false,
    "pause": false
}
```

`op` - This is the opcode that Lavalink requires. What we are sending is the `play` opcode, which tells Lavalink to play a song.

`guildId` - This is the ID of the guild that the song is being played in.

`track` - This is the track that is being played.

`startTime` - This is the start time of the song. Useful when you only want to start from a certain point in the song.

`endTime` - This is the end time of the song. Useful when you only want to play a certain part of the song.

`volume` - This value sets the volume of the song.

`noReplace` - This is a boolean value that tells Lavalink whether to replace the current song.

`pause` - This is a boolean value that tells Lavalink whether to pause the current song.

Keep in mind, that this is just for illustration purposes.

## Lavalink Configuration
Lavalink can be configured by using a file called ``application.yml``. 
It is a configuration file, where you can define port/host to open a connection and a lot of different options.
For example:
```yaml
server: # REST and WS server
  port: 2333  # port to open
  address: 127.0.0.1  # the address to open
lavalink:
  server:
    password: "youshallnotpass"  # password for the for authentication.
    sources:
      youtube: true
      bandcamp: true
      soundcloud: true
      twitch: false
      vimeo: true
      http: true
      local:  true
    bufferDurationMs: 200  # JDA buffer duration
    youtubePlaylistLoadLimit: 6 # Number of pages at 100 each
    youtubeSearchEnabled: true  # This enables the YouTube search feature.
    soundcloudSearchEnabled: true # This enables the SoundCloud search feature.
    gc-warnings: true  # This enables garbage collection warnings.
    #ratelimit:
      #ipBlocks: ["1.0.0.0/8", "..."] # list of ip blocks
      #excludedIps: ["...", "..."] # ips which should be explicit excluded from usage by lavalink
      #strategy: "RotateOnBan" # RotateOnBan | LoadBalance | NanoSwitch | RotatingNanoSwitch
      #searchTriggersFail: true # Whether a search 429 should trigger marking the ip as failing
      #retryLimit: -1 # -1 = use default lavaplayer value | 0 = infinity | >0 = retry will happen this numbers times

metrics:
  prometheus:
    enabled: false
    endpoint: /metrics

sentry:
  dsn: ""
#  tags:
#    some_key: some_value
#    another_key: another_value

logging:
  file:
    max-history: 30
    max-size: 1GB
  path: ./logs/

  level:
    root: INFO
    lavalink: INFO
```
This is an example of a configuration file, as you can see you have loads of different options, you can play with.
The most notable ones are:

`server` - This is where you configure the REST and websocket port and address.

`lavalink` - This is where you configure the Lavalink server itself.

`sources` - This is where you configure the sources that Lavalink will use.

`metrics` - Metrics is a feature that allows you to expose metrics to Prometheus.

`sentry` - Sentry is a feature that allows you to log exceptions to Sentry and monitor them.

`logging` - This is where you configure the logging, Lavalink uses logging to log errors, warnings and information. It is very useful, and you should keep it enabled.

If you want to know more about Lavalink, visit this repository:
[Click here to visit](https://github.com/freyacodes/Lavalink)

Also, visit the Lavaplayer repository:
[Click here to visit](https://github.com/sedmelluq/Lavaplayer)

## What is Wavelink?
Wavelink is a powerful and robust wrapper around Lavalink that is written in `python`. 
Wavelink abstracts away the complexities regarding Lavalink and makes it easier for us to use.
It supports everything that Lavalink provides, but it also provides additional features.

# What is Jishaku?
Jishaku is an extension developed for bot developers that enables rapid prototyping, experimentation, and 
debugging of their bots. It allows us to debug, test, and experiment with our bots through discord. It has a lot of features, and it is extremely useful.
Again, Jishaku has been rewritten to support disnake for this project.
Jishaku is only usable by the owner of the bot. To use jishaku, you can use the command <your bot prefix>`jishaku`, or its alias `jsk`.
Most notable features of Jishaku are:

1.) To be able to run python code from discord.
2.) You can interact with your environment and your terminal, through your bot.
3.) You can interact with your bot extensions, through your bot. For example, loading / unloading extensions.
4.) You can interact with your bot, through your bot. For example, reloading the bot.
and more.

To know more about Jishaku, visit this repository: 
[Click here to visit](https://github.com/Gorialis/Jishaku)

## How to run this.
1.) In your favorite web browser, navigate to [Discord Developer Portal](https://discord.com/developers/applications):

2.) Create your own __bot account__.

3.) Enable Privileged Intents - Member Intents - Presence Intents - Message Intents. (**Very Important!**)

4.) Go in `OAuth2` tab and enable ``applications.commands`` and `bot` scope, so that your bot can have slash commands.

6.) Then run ``main.py`` file in your preferred code editor/IDE, by either pressing F5 or running it through the terminal.

```bash
python3 main.py
```
If you want to use poetry, you can run the following command:

```bash
poetry run task bot
```

## Credits
Well, this project is entirely free and Open Source, if you want, you can certainly use it in your own projects.
If you like this project, you can add a GitHub star to show your appreciation, and you can credit me in your project.
Thanks :)
Have a nice day!
