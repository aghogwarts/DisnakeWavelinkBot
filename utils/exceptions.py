from disnake.ext import commands


class NoChannelProvided(commands.CommandError):
    """
    Error raised when no suitable voice channel was supplied.
    """

    pass


class IncorrectChannelError(commands.CommandError):
    """
    Error raised when commands are issued outside the players' session channel.
    """

    pass
