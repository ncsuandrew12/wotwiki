import argparse
import asyncio
import sys
import threading
import discord
import json
import pathlib
from discord.ext import commands

import utils
from command import Command, Progresser, Verbosity, run_command

class DiscordBot(commands.Bot):
    def __init__(self, manager, shared_dict):
        intents = discord.Intents.default()
        intents.message_content = True
        commands.Bot.__init__(self, command_prefix='!', intents=intents)
        self.manager = manager
        self.shared_dict = shared_dict

    async def on_ready(self):
        self.manager.print_n(f'We have logged in as {self.user}')
        self.shared_dict["ready"] = True

    def send_message(self, channel, message):
        # # TODO: Queue the message and return
        # # self.manager.print_n(f'Channel: {channel}, message: {message}')
        # # Schedule the coroutine on the bot's event loop from another thread
        # future = asyncio.run_coroutine_threadsafe(channel.send(message), self.loop)
        # # Optionally wait for the result if needed
        # future.result(timeout=30)
        pass

class DiscordBotManager(Command):

    def __init__(self, args):
        Command.__init__(self, args)

    def create_arg_parser(self):
        parser = argparse.ArgumentParser(
            description=""
        )
        return parser

    def run_command(self):
        self.print_n("Starting Discord bot thread...", end="", flush=True)
        progresser = Progresser(self)
        self.shared_dict = { "ready": False }
        self.bot = DiscordBot(self, self.shared_dict)
        # Required: Create and set a new event loop for this specific thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        bot_thread = threading.Thread(target=self.run_bot_thread, daemon=True)
        bot_thread.start()
        while not self.shared_dict.get("ready", False):
            progresser.tick()
        (self.parsed_args.verbosity == Verbosity.NORMAL) and print("")
        self.print_n("Discord bot thread started.")
        return 0

    def run_bot_thread(self):
        with open(pathlib.Path.home() / ".wotwiki-dev-bot" / "secret.json", "r") as f:
            secret_json = json.load(f)
        self.bot.run(secret_json['token'])