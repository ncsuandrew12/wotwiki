import asyncio
import threading

from discord_bot import DiscordBot
from progresser import Progresser
from thread_safe_dict import ThreadSafeDict
from wotwiki_cfg import secrets_json

class DiscordBotter():
    ready = False

    def __init__(self):
        self.shared_dict = ThreadSafeDict()
        self.shared_dict["ready"] = False
        self.bot = DiscordBot(self, self.shared_dict)

    def run(self):
        if not self.ready:
            print("Starting Discord bot thread...")
            progresser = Progresser()
            # Required: Create and set a new event loop for this specific thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            bot_thread = threading.Thread(target=self.run_bot_thread, daemon=True)
            bot_thread.start()
            while not self.shared_dict.get("ready", False):
                progresser.tick()
            progresser.done()
            print("Discord bot thread started.")
            self.ready = True
        else:
            print("Discord bot thread already running.")
        return 0

    def run_bot_thread(self):
        self.bot.run(secrets_json['discord-token'])

botter = DiscordBotter()