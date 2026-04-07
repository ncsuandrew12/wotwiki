# This script requires pywikibot to be properly configured with a families/wot_family.py and a user file.
# Example user file for a bot named "androlf-bot" for a user named "androlf":
# Filename: Androlf@androlf-bot_password.py
# Contents:
#('Androlf', BotPassword('androlf-bot', 'putThePasswordHere'))

import argparse
import os
import pathlib
from time import sleep
import pywikibot
import re
import sys
from pywikibot import pagegenerators

import discord_bot
from discord_bot import DiscordBotManager
from command import Command, Verbosity, run_command
from log_utils import logger as log
from utils import Ticker

language = "en"
mod_queue_dir_path = pathlib.Path.home() / ".wotwiki" / "mod_queue"
mod_queue_json_path = mod_queue_dir_path / "queue.json"
wiki_name = "wot"

class DownloadWiki(Command):

    def __init__(self, args):
        Command.__init__(self, args)
        self.bot = None
        self.log_channel = None

    def create_arg_parser(self):
        parser = argparse.ArgumentParser(
            description="Download everything on the wiki."
        )
        parser.add_argument(
            "--include-images",
            action="store_true",
            default=False,
            help="If set, the script will include images in the download.")
        parser.add_argument(
            "--out-dir",
            action="store",
            default="./wot.fandom.com",
            help="Directory to store the downloads.")
        return parser
    
    def run_command(self):
        try:
            self.site = None
            self.preloaded_pages = None
            intro_log = f"Running downloader for {wiki_name} wiki."
            log.info(intro_log)
            self.process_args()
            # Set the pywikibot directory to be one level up on the active file path which gives it visibility of the local user-config, password file and families.
            os.environ["PYWIKIBOT_DIR"] = os.path.abspath("../")
            self.site = pywikibot.Site("en", wiki_name)
            self.site.login()
            login_log = f"Logged into wiki {wiki_name} successfully!"
            self.print_n(login_log)
            self.bot = DiscordBotManager([discord_bot.__file__]) # TODO: Pass along verbosity args
            rc = run_command(self.bot)
            if rc != 0:
                exit(rc)
            self.log_channel = self.bot.bot.get_channel(1489504714386309150) # TODO hard-coded channel id
            self.bot.bot.send_message(self.log_channel, f"# {intro_log}")
            self.bot.bot.send_message(self.log_channel, login_log)
            page_cnt = 0
            failed_pages = []
            ticker = Ticker(10)
            for ns in self.site.namespaces:
                self.print_n(f"Namespace {ns}", end="", flush=True)
                if int(ns) in [-2, -1]: # Skip images and special
                    self.print_n("")
                    self.print_n(f"Skipping namespace {ns}")
                    continue
                # TODO: Don't skip the canonical namespaces
                if int(ns) >= 0 and int(ns) <= 15:
                    self.print_n("")
                    self.print_n(f"Skipping namespace {ns}")
                    continue
                all_pages_gen = self.site.allpages(namespace=ns)
                self.preloaded_pages = pagegenerators.PreloadingGenerator(all_pages_gen, groupsize=50, quiet=True)
                first_status_log = True
                ticker.restart()
                # TODO Get version of page as it existed when script started runnning.
                for page in self.preloaded_pages:
                    if ticker.tick() == True:
                        if not first_status_log and (self.parsed_args.verbosity == Verbosity.NORMAL):
                            print("")
                            self.print_n(f"{page_cnt:5d} pages read. {len(failed_pages):5d} pages produced errors.", end="", flush=True)
                        first_status_log = False
                        sleep(ticker.period - 5)
                    (self.parsed_args.verbosity == Verbosity.NORMAL) and print(".", end="", flush=True)
                    log.debug("Processing page: %s", page.title())
                    try:
                        page.get(get_redirect=True)
                        os.makedirs(mod_queue_dir_path, exist_ok=True)
                        filename = self.sanitize_str_for_filename(page.title())
                        page_path = f"{self.parsed_args.out_dir}/{filename}.wiki"
                        os.makedirs(os.path.dirname(page_path), exist_ok=True)
                        if pathlib.Path(page_path).exists():
                            raise Exception(f"Page path {page_path} already exists, skipping page '{page.title()}'.")
                        with open(page_path, "w") as f:
                            f.write(page.text)
                    except Exception as e:
                        err_log = f"Error processing page '{page.title()}':"
                        log.error(err_log, exc_info=True)
                        if self.bot and self.log_channel:
                            self.bot.bot.send_message(self.log_channel, f"{err_log} {e}")
                        failed_pages.append(page.title())
                    page_cnt = page_cnt + 1
                log.warning(f"Failed pages: {failed_pages}")
                (self.parsed_args.verbosity == Verbosity.NORMAL) and print("")
                self.print_n(f"{page_cnt} pages read. {len(failed_pages)} pages produced errors.")
        except Exception as e:
            log.error(e)
            if self.bot and self.log_channel:
                self.bot.bot.send_message(self.log_channel, f"Error during mass download: {e}")
            raise
        return 0

    def print(self, verbosity, msg, end="\n", flush=False):
        if Command.print(self, verbosity, msg, end=end, flush=flush):
            if self.bot and self.log_channel:
                self.bot.bot.send_message(self.log_channel, f"`{msg}`")

    def process_args(self):
        log.debug("Processing arguments.")

    def sanitize_str_for_filename(self, s):
        s = re.sub(r"[^a-zA-Z0-9_\-\\\/ \'\:]", "_", s)
        return s

exit(run_command(DownloadWiki(sys.argv)))