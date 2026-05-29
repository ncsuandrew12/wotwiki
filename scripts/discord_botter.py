import asyncio
import json
import os
import pathlib
from progresser import Progresser
import threading
from discord_bot import DiscordBot
from thread_safe_dict import ThreadSafeDict

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
        cfg_path = os.getenv("WOTWIKI_DISCORD_CFG_PATH", pathlib.Path.home() / ".wotwiki-dev-bot" / "secret.json")
        with open(cfg_path, "r") as f:
            secret_json = json.load(f)
        self.bot.run(secret_json['token'])

botter = DiscordBotter()