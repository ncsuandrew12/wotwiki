import logging
from logging.handlers import RotatingFileHandler
import os
import pathlib
import sys

formatter = None
stderrHandler = None

class MaxLogLevelFilter(logging.Filter):
    def __init__(self, logLevel):
        self.logLevel = logLevel

    def filter(self, record):
        return record.levelno <= self.logLevel

    logLevel = logging.DEBUG

class Formatter(logging.Formatter):
    def format(self, record):
        record.timeZone = "EST"
        record.levelnameSuffix = (" " * (len("CRITICAL") - len(record.levelname)))
        return logging.Formatter.format(self, record)

def get_logger(name):
    global formatter
    global stderrHandler
    formatter = Formatter(
        fmt="%(asctime)s %(timeZone)s %(processName)s:%(threadName)s %(levelname)s:%(levelnameSuffix)s %(pathname)s:%(lineno)d(%(funcName)s) %(message)s",
        datefmt=None)
    logDir = os.path.join(pathlib.Path.home(), ".wotwiki", "logs")
    os.makedirs(logDir, exist_ok=True)
    fileHandler = RotatingFileHandler(
        filename=os.path.join(logDir, f"wotwiki.log"),
        maxBytes=5 * 1024 * 1024, # 5MB
        backupCount=9,
        delay=True)
    fileHandler.setFormatter(formatter)
    logger = logging.getLogger(name)
    stdoutHandler = logging.StreamHandler(stream=sys.stdout)
    stdoutHandler.setFormatter(formatter)
    stderrHandler = logging.StreamHandler(stream=sys.stderr)
    stderrHandler.setFormatter(formatter)
    logger.addHandler(fileHandler)
    logger.addHandler(stderrHandler)
    logging.getLogger().setLevel(logging.NOTSET)
    stdoutHandler.setLevel(logging.INFO)
    stdoutHandler.addFilter(MaxLogLevelFilter(logging.WARNING))
    stderrHandler.setLevel(logging.ERROR)
    return logger

logger = get_logger("wotwiki")