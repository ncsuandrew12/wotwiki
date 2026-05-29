import asyncio
import discord
from discord.ext import commands

class DiscordBot(commands.Bot):
    def __init__(self, manager, shared_dict):
        intents = discord.Intents.default()
        intents.message_content = True
        commands.Bot.__init__(self, command_prefix='!', intents=intents)
        self.manager = manager
        self.shared_dict = shared_dict

    async def on_ready(self):
        print(f'Logged in as {self.user}')
        self.shared_dict["ready"] = True

    def send_message(self, channel, message):
        # TODO: Queue the message and return
        # self.manager.print_n(f'Channel: {channel}, message: {message}')
        # Schedule the coroutine on the bot's event loop from another thread
        future = asyncio.run_coroutine_threadsafe(channel.send(message), self.loop)
        # Optionally wait for the result if needed
        future.result(timeout=30)