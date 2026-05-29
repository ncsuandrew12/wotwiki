import logging
from logging.handlers import RotatingFileHandler
import os
import pathlib
import pywikibot
import sys

from discord_botter import botter
from discord_logger import DWP, DiscordTextChannelHandler
from wotwiki_cfg import cfg_json

class Filter(logging.Filter):
    def filter(self, record):
        if record.args:
            new_args = tuple(
                DWP(arg) if isinstance(arg, pywikibot.Page) else arg
                for arg in record.args
            )
            record.args = new_args
        return True

class MaxLogLevelFilter(logging.Filter):
    logLevel = logging.DEBUG

    def __init__(self, logLevel):
        self.logLevel = logLevel

    def filter(self, record):
        return record.levelno <= self.logLevel

class Formatter(logging.Formatter):
    def format(self, record):
        record.timeZone = "EST"
        record.levelnameSuffix = (" " * (len("CRITICAL") - len(record.levelname)))
        # if record.args:
        #     new_args = tuple(
        #         f"'{DWP(arg.title())}'" if isinstance(arg, pywikibot.Page) else arg
        #         for arg in record.args
        #     )
        #     record.args = new_args
        return super().format(record)

class DiscordFormatter(Formatter):
    def format(self, record):
        if record.args:
            new_args = tuple(
                f"{arg.__to_discord_str__()}" if hasattr(arg, '__to_discord_str__') else arg
                for arg in record.args
            )
            record.args = new_args
        return super().format(record)

def setup_logger(logger, discordChannelId=None):
    global formatter
    global stdoutHandler
    global stderrHandler
    global discordStdFormatter
    global discordErrFormatter
    logger.addFilter(Filter())
    logger.addHandler(fileHandler)
    logger.addHandler(stdoutHandler)
    logger.addHandler(stderrHandler)
    if discordChannelId is not None:
        if not botter.ready:
            errorCode = botter.run()
            if errorCode != 0:
                raise Exception(f"Error starting Discord bot: {errorCode}")
        channel = botter.bot.get_channel(discordChannelId)
        discordStdHandler = DiscordTextChannelHandler(channel)
        discordStdHandler.setFormatter(discordStdFormatter)
        discordStdHandler.setLevel(logging.INFO)
        discordStdHandler.addFilter(MaxLogLevelFilter(logging.INFO))
        discordErrHandler = DiscordTextChannelHandler(channel)
        discordErrHandler.setFormatter(discordErrFormatter)
        discordErrHandler.setLevel(logging.WARNING)
        logger.addHandler(discordStdHandler)
        logger.addHandler(discordErrHandler)
    return logger

logging.getLogger().setLevel(logging.NOTSET)
logDir = os.path.join(pathlib.Path.home(), ".wotwiki", "logs")
os.makedirs(logDir, exist_ok=True)
formatter = Formatter(
        fmt="%(asctime)s %(timeZone)s %(processName)s:%(threadName)s %(levelname)s:%(levelnameSuffix)s %(pathname)s:%(lineno)d(%(funcName)s) %(message)s",
        datefmt=None)
discordStdFormatter = DiscordFormatter(
    fmt="`%(asctime)s %(timeZone)s %(processName)s:%(threadName)s %(levelname)s:%(levelnameSuffix)s` [%(filename)s:%(lineno)d(%(funcName)s)](https://github.com/wotwiki/wotwiki/blob/master/scripts/%(filename)s#L%(lineno)d)\n%(message)s",
    datefmt=None)
discordErrFormatter = DiscordFormatter(
    fmt="# %(levelname)s\n`%(asctime)s %(timeZone)s %(processName)s:%(threadName)s` [%(filename)s:%(lineno)d(%(funcName)s)](https://github.com/wotwiki/wotwiki/blob/master/scripts/%(filename)s#L%(lineno)d)\n**%(message)s**",
    datefmt=None)
fileHandler = RotatingFileHandler(
    filename=os.path.join(logDir, f"wotwiki.log"),
    maxBytes=5 * 1024 * 1024, # 5MB
    backupCount=9,
    delay=True)
fileHandler.setFormatter(formatter)
stderrHandler = logging.StreamHandler(stream=sys.stderr)
stderrHandler.setFormatter(formatter)
stderrHandler.setLevel(logging.ERROR)
stdoutHandler = logging.StreamHandler(stream=sys.stdout)
stdoutHandler.setFormatter(formatter)
stdoutHandler.setLevel(logging.WARNING)
stdoutHandler.addFilter(MaxLogLevelFilter(logging.WARNING))
logger = logging.getLogger("wotwiki")
setup_logger(logger, discordChannelId=cfg_json["discord_log_channel_id"] or None)