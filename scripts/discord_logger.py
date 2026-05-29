import asyncio
import discord
from discord.ext import commands
import json
import logging
import pathlib
from progresser import Progresser
import threading

class DiscordBot(commands.Bot):
    def __init__(self, manager, shared_dict):
        intents = discord.Intents.default()
        intents.message_content = True
        commands.Bot.__init__(self, command_prefix='!', intents=intents)
        self.manager = manager
        self.shared_dict = shared_dict

    async def on_ready(self):
        print(f'We have logged in as {self.user}')
        self.shared_dict["ready"] = True

    def send_message(self, channel, message):
        # TODO: Queue the message and return
        # self.manager.print_n(f'Channel: {channel}, message: {message}')
        # Schedule the coroutine on the bot's event loop from another thread
        future = asyncio.run_coroutine_threadsafe(channel.send(message), self.loop)
        # Optionally wait for the result if needed
        future.result(timeout=30)

class DiscordBotter():

    def run(self):
        print("Starting Discord bot thread...")
        progresser = Progresser()
        self.shared_dict = { "ready": False }
        self.bot = DiscordBot(self, self.shared_dict)
        # Required: Create and set a new event loop for this specific thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        bot_thread = threading.Thread(target=self.run_bot_thread, daemon=True)
        bot_thread.start()
        while not self.shared_dict.get("ready", False):
            progresser.tick()
        progresser.done()
        print("Discord bot thread started.")
        return 0

    def run_bot_thread(self):
        with open(pathlib.Path.home() / ".wotwiki-dev-bot" / "secret.json", "r") as f:
            secret_json = json.load(f)
        self.bot.run(secret_json['token'])

class DiscordTextChannelHandler(logging.Handler):
    """
    A handler class which writes logging records, appropriately formatted,
    to a Discord text channel.
    """

    botter = DiscordBotter()
    channelId = None
    channel = None

    def __init__(self, channelid=None):
        """
        Initialize the handler. Setup the bot and get the target channel.
        """
        logging.Handler.__init__(self)
        self.channelId = channelid

    def emit(self, record):
        if self.channel is None:
            errorCode=self.botter.run()
            if errorCode != 0:
                raise Exception(f"Error starting Discord bot: {errorCode}")
            self.channel = self.botter.bot.get_channel(self.channelId)

        """
        Emit a record.

        If a formatter is specified, it is used to format the record.
        The record is then written to the stream with a trailing newline.  If
        exception information is present, it is formatted using
        traceback.print_exception and appended to the stream.  If the stream
        has an 'encoding' attribute, it is used to determine how to do the
        output to the stream.
        """
        try:
            msg = self.format(record)
            self.botter.bot.send_message(self.channel, f"{msg}")
        # except RecursionError:  # See issue 36272
        #     raise
        except Exception:
            self.handleError(record)

    def __repr__(self):
        return '<%s %s(%s)>' % (self.__class__.__name__, self.channelId, logging.getLevelName(self.level))

#     __class_getitem__ = classmethod(logging.GenericAlias)