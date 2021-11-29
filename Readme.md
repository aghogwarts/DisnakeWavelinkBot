# Music Bot

An example music bot that is written in Disnake [Maintained discord.py Fork] 

## Disnake 
Disnake is a maintained and updated fork of `discord.py`.

[Disnake Github Repo](https://github.com/DisnakeDev/disnake)


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

Lavalink.jar file is too big to be included in the repository, so you have to install it yourself in the directory 
``lavalink``.

Visit [Lavalink 3.4](https://github.com/freyacodes/Lavalink/releases/tag/3.4) to download the latest version. 
Make sure you have JDK 8 or JDK 13 installed.

Install Lavalink.jar in the directory ``lavalink`` and that's it.
## What is Lavalink and how this music bot works??

Lavalink is a standalone audio streaming node written in Java that is based on `Lavaplayer`(An audio player written in Java).

Lavalink creates a  REST and websocket server where our application needs to connect to. Once connected, we need to send OPcodes
that Lavalink requires, through websocket that Lavalink created.

For example, if we want to play a song, we need to send the following through websocket:
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
`guildId` - This is the guild id of the guild that the song is being played in.
`track` - This is the track that is being played.
`startTime` - This is the start time of the song. Useful when you only want to start from a certain point in the song.
`endTime` - This is the end time of the song.
`volume` - This is the volume of the song.
`noReplace` - This is a boolean value that tells Lavalink whether to replace the current song.
`pause` - This is a boolean value that tells Lavalink whether to pause the current song.

Keep in mind, that this is just for illustration purposes.

## Configuration
Lavalink can be configured by using a file called ``application.yml``. 
It is a configuration file, where you can define port/host to open a connection and a lot of different options.
For example:
```yaml
server: # REST and WS server
  port: 2333
  address: 127.0.0.1
lavalink:
  server:
    password: "youshallnotpass"
    sources:
      youtube: true
      bandcamp: true
      soundcloud: true
      twitch: false
      vimeo: true
      mixer: false
      http: true
      local:  true
    bufferDurationMs: 400
    youtubePlaylistLoadLimit: 6 # Number of pages at 100 each
    youtubeSearchEnabled: true
    soundcloudSearchEnabled: true
    gc-warnings: true
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
`server` - This is where you configure the REST and websocket ports and address.
`lavalink` - This is where you configure the Lavalink server itself.
`metrics` - This is the metrics server.
`sentry` - This is the sentry server.
`logging` - This is where you configure the logging, Lavalink uses logging to log errors, warnings and information. It is very useful and you should keep it enabled.

## Wavelink
Here comes Wavelink, A powerful and robust wrapper around Lavalink that is written for `python`.
It abstracts away all the complexities of Lavalink and makes it easy for us play our favourite music tracks in it, 
with your discord bot application.
Wavelink supports all the features of Lavalink (my version of it.).

If you want to know more about Lavalink, visit this repository:
[Click here to visit](https://github.com/freyacodes/Lavalink)

Also visit this repository:
[Click here to visit](https://github.com/sedmelluq/Lavaplayer)

## How to run this.
1.) In a web browser, navigate to [Discord Developer Portal](https://discord.com/developers/applications):

2.) Create your own __bot account__.

3.) Enable Privileged Intents - Member Intents/Presence Intents/Message Intents. (Very Important)

4.) Go in `Oauth2` tab and enable ``applications.commands`` and `bot` scope to make sure your bot can have slash commands.

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
