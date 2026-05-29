import logging
import pywikibot
import re
import wikitextparser
from discord_botter import botter

class DiscordLogger():
    botter = None
    channel = None

    def __init__(self, channel):
        self.botter = botter
        self.channel = channel

    def send_message(self, message):
        self.botter.bot.send_message(self.channel, f"{message}")

class DiscordTextChannelHandler(logging.Handler):
    """
    A handler class which writes logging records, appropriately formatted,
    to a Discord text channel.
    """
    messenger = None

    def __init__(self, channel):
        """
        Initialize the handler. Setup the bot and get the target channel.
        """
        logging.Handler.__init__(self)
        self.messenger = DiscordLogger(channel)

    def emit(self, record):
        """
        Emit a record.

        If a formatter is specified, it is used to format the record.
        The record is then written to the stream with a trailing newline.  If
        exception information is present, it is formatted using
        traceback.print_exception and appended to the stream.
        """
        try:
            msg = self.format(record)
            self.messenger.send_message(f"{msg}")
        # except RecursionError:  # See issue 36272
        #     raise
        except Exception:
            self.handleError(record)

    def __repr__(self):
        return '<%s %s(%s)>' % (self.__class__.__name__, self.channelId, logging.getLevelName(self.level))

#     __class_getitem__ = classmethod(logging.GenericAlias)

class DiscordText():
    str = ""
    dis = ""

    def __init__(self, text, dis):
        self.str = text
        self.dis = dis

    def __str__(self):
        return self.str

    def __to_discord_str__(self):
        return self.dis

class DH1(DiscordText):
    def __init__(self, text):
        super().__init__(text, f"# {text}")

class DWP(DiscordText):
    def __init__(self, page):
        if isinstance(page, pywikibot.Page):
            page = page.title()
        super().__init__(f"'{page}'", f"[{page}](https://wot.fandom.com/wiki/{re.sub(r'\s', '_', page.strip())})")

class DWT(DWP):
    def __init__(self, template):
        if isinstance(template, wikitextparser.Template):
            template = template.name
        template = f"Template:{template}"
        super().__init__(template)
