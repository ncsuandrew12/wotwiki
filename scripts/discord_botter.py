import asyncio
import json
import pathlib
from progresser import Progresser
import threading
from discord_bot import DiscordBot

class DiscordBotter():
    ready = False

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
        self.ready = True
        return 0

    def run_bot_thread(self):
        with open(pathlib.Path.home() / ".wotwiki-dev-bot" / "secret.json", "r") as f:
            secret_json = json.load(f)
        self.bot.run(secret_json['token'])
