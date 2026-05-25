# This script requires pywikibot to be properly configured with a families/wot_family.py and a user file.
# Example user file for a bot named "androlf-bot" for a user named "androlf":
# Filename: Androlf@androlf-bot_password.py
# Contents:
#('Androlf', BotPassword('androlf-bot', 'putThePasswordHere'))

import argparse
import discord
import json
import os
import pathlib
import pywikibot
import re
import shutil
import sys
import urllib.parse
import wikitextparser as wtp
from pathlib import Path
from pywikibot import pagegenerators, sleep
from pywikibot.exceptions import NoPageError


import discord_bot
import utils
from discord_bot import DiscordBotManager
from command import Command, Verbosity, run_command
from log_utils import logger as log
from page_mod import PageMod, PageModifier
from utils import Ticker

language = "en"
mod_queue_dir_path = pathlib.Path.home() / ".wotwiki" / "mod_queue"
mod_queue_json_path = mod_queue_dir_path / "queue.json"
wiki_name = "wot"

class SyncCharactersJsonWithWikiPages(Command):

    def __init__(self, args):
        Command.__init__(self, args)
        self.bot = None
        self.log_channel = None

    def create_arg_parser(self):
        parser = argparse.ArgumentParser(
            description="Sync characters JSON with wiki pages."
        )
        parser.add_argument(
            "--character-json",
            action="store",
            default="./wiki/Module:Characters/characters.json",
            help="Path to the characters JSON file.")
        parser.add_argument(
            "--save-changes",
            action="store_true",
            default=False,
            help="If not set, the script will not save changes to the wiki, regardless of prompts.")
        parser.add_argument(
            "--non-interactive",
            action="store_true",
            default=False,
            help="If set, the script will run in non-interactive mode and will not prompt for confirmation before saving changes.")
        parser.add_argument(
            "--changes-all-file",
            action="store",
            default="./changes-all.patch",
            help="File to store diff of all changes.")
        parser.add_argument(
            "--change-summary-prefix",
            action="store",
            default="bot character json-to-wiki sync",
            help="Prefix to use for change summaries when saving changes.")
        parser.add_argument(
            "--discard-queue",
            action="store_true",
            default=False,
            help="If set, the script will discard the modification queue before processing.")
        return parser
    
    def run_command(self):
        q = json.load(open("/home/andrewf/w/wotwiki/scratch/wiki/Module:Quotes/quotes.json", "r"))
        q["tags"] = dict(sorted(q["tags"].items()))
        with open("/home/andrewf/w/wotwiki/scratch/wiki/Module:Quotes/quotes_sorted.json", "w") as f:
            json.dump(q, f, indent=4)
        try:
            self.site = None
            self.preloaded_pages = None
            intro_log = f"Running character sync for {wiki_name} wiki."
            log.info(intro_log)
            self.process_args()
            no_save_log = None
            if not self.parsed_args.save_changes:
                no_save_log = f"self.parsed_args.save_changes is {self.parsed_args.save_changes}, this run {self.parsed_args.save_changes and 'MAY' or 'WILL NOT'} save changes to the wiki!"
                log.warning(no_save_log)
            # Set the pywikibot directory to be one level up on the active file path which gives it visibility of the local user-config, password file and families.
            os.environ["PYWIKIBOT_DIR"] = os.path.abspath("../")
            # print("env: " + os.environ["PYWIKIBOT_DIR"])
            # wiki_name comes from variables above, i.e. domo.fandom.com this wiki_name variable would be "domo"
            self.site = pywikibot.Site("en", wiki_name)
            self.site.login()
            login_log = f"Logged into wiki {wiki_name} successfully!."
            self.print_n(login_log)
            self.bot = DiscordBotManager([discord_bot.__file__]) # TODO: Pass along verbosity args
            rc = run_command(self.bot)
            if rc != 0:
                exit(rc)
            self.log_channel = self.bot.bot.get_channel(1489504714386309150)
            self.bot.bot.send_message(self.log_channel, f"# {intro_log}")
            self.bot.bot.send_message(self.log_channel, login_log)
            if no_save_log:
                self.bot.bot.send_message(self.log_channel, no_save_log)
            if Path(mod_queue_dir_path).is_dir() and self.parsed_args.discard_queue:
                self.print_n(f"Discarding modification queue at {mod_queue_dir_path}.")
                shutil.rmtree(mod_queue_dir_path)
            if not Path(mod_queue_dir_path).is_dir():
                self.create_queue()
            if Path(mod_queue_dir_path).is_dir():
                self.process_queue()
        except Exception as e:
            log.error(e)
            if self.bot and self.log_channel:
                self.bot.bot.send_message(self.log_channel, f"Error during char sync: {e}")
            raise
        return 0

    def print(self, verbosity, msg, end="\n", flush=False):
        if Command.print(self, verbosity, msg, end=end, flush=flush):
            if self.bot and self.log_channel:
                self.bot.bot.send_message(self.log_channel, f"`{msg}`")

    def process_args(self):
        log.debug("Processing arguments.")
        self.parsed_args.change_summary_prefix = self.parsed_args.change_summary_prefix.strip()

    def sanitize_str_for_filename(self, s):
        # s = re.sub(r"\s+", "_", s)
        s = re.sub(r"\u2019", "", s)
        s = re.sub(r"[^a-zA-Z0-9_\-\\\/ \'\:]", "", s)
        # s = re.sub(r"_+", "_", s)
        return s

    def create_queue(self):
        mod_queue = []
        still_dirty = []
        page_cnt = 0
        page_id = 1
        pages_noperm = 0
        failed_pages = []
        missing_pages = []
        queued_pages = []
        ticker = Ticker()
        chars = json.load(open(self.parsed_args.character_json, "r"))
        first_status_log = True
        with open(f"{self.parsed_args.changes_all_file}", "w") as all_changes_file:
            for char in chars:
                if ticker.tick():
                    if not first_status_log:
                        (self.parsed_args.verbosity == Verbosity.NORMAL) and print("")
                        self.print_n(f"{page_cnt:5d}/{len(chars)} characters processed. {len(queued_pages):5d} queued. {pages_noperm:5d} skipped due to perms. {len(failed_pages):5d} pages produced errors.", end="", flush=True)
                    first_status_log = False
                name = chars[char].get("name") or char
                page = chars[char].get("page") or char or name
                if page is None:
                    failed_pages.append(str(char))
                    raise Exception("Character '{}' does not have a name or page field in the JSON.".format(char))
                self.print_v(f"Character {name}", end="", flush=True)
                page = pywikibot.Page(self.site, page)
                (self.parsed_args.verbosity == Verbosity.NORMAL) and print(".", end="", flush=True)
                log.debug("Processing page: %s", page.title())
                try:
                    try:
                        attempts = 3
                        while attempts > 0:
                            try:
                                page.get(get_redirect=True)
                                attempts = 0
                            except KeyboardInterrupt as e:
                                log.warning("KeyboardInterrupt received.", exc_info=True)
                                sleep(3)
                            attempts -= 1
                    except NoPageError as e:
                        missing_pages.append(page.title())
                        raise
                    pre_text = page.text
                    mod = PageMod(page_id, urllib.parse.unquote(page.title()), [self.parsed_args.change_summary_prefix])
                    parsed = wtp.parse(page.text)
                    for template in parsed.templates:
                        if template.name.strip().lower() == "character":
                            name = chars[char].get("name")
                            if name:
                                for param in template.arguments:
                                    param_name = param.name.strip().lower()
                                    if param_name == "name":
                                        name = re.sub(r"\s*\(.*$", "", name).strip()
                                        val = param.value.strip()
                                        if val and len(val) > 0 and val != name:
                                            log.warning(f"Name mismatch for character '{char}' on page '{page.title()}': JSON name is '{name}' but wiki page has '{val}'.")
                                        param.value = name
                                # elif param_name == "aliases":
                                #     param.value = chars[char].get("aliases") or ""
                                # elif param_name == "description":
                                #     param.value = chars[char].get("description") or ""
                    # TODO update page
                    if pre_text != page.text:
                        mod_path = f"{mod_queue_dir_path}/{self.sanitize_str_for_filename(mod.title)}"
                        os.makedirs(mod_queue_dir_path, exist_ok=True)
                        pre_path = f"{mod_path}/pre.wiki"
                        post_path = f"{mod_path}/post.wiki"
                        os.makedirs(os.path.dirname(pre_path), exist_ok=True)
                        with open(pre_path, "w") as f:
                            f.write(pre_text)
                        os.makedirs(os.path.dirname(post_path), exist_ok=True)
                        with open(post_path, "w") as f:
                            f.write(page.text)
                        subp = utils.run_subprocess(
                            cmdArgs = ["diff", "-auprN", pre_path, post_path],
                            shell=False,
                            timeout=0,
                            throwOnStdErr=True,
                            expectedReturnCode=1,
                            throwOnUnexpectedReturnCode=True,
                            logAndReturnStdout=True,
                            stdoutFilePath=None,
                            stderrFilePath=None)
                        all_changes_file.write(subp.stdout)
                        all_changes_file.write("\n")
                        deduped_summary = []
                        for line in mod.summary:
                            if line not in deduped_summary:
                                deduped_summary.append(line)
                        mod.summary = " ".join(deduped_summary)
                        if (page.botMayEdit()):
                            log_msg = f"Page '{page.title()}' needs update; queuing. Summary: {mod.summary}"
                            log.info(log_msg)
                            self.bot.bot.send_message(self.log_channel, log_msg)
                            mod_queue.append(mod)
                            queued_pages.append(mod.title)
                            page_id += 1
                            with open(f"{mod_path}/changes.patch", "w") as changes_file:
                                changes_file.write(subp.stdout)
                                changes_file.write("\n")
                        else:
                            page.text = pre_text
                            log.warning(f"Page '{page.title()}' needs update but bot is not allowed to edit it. Summary: {mod.summary}")
                            self.bot.bot.send_message(self.log_channel, f"Page '{page.title()}' needs update but bot is not allowed to edit it. Summary: {mod.summary}")
                            pages_noperm += 1
                except Exception as e:
                    exc_info = True
                    err_log = f"Error processing page '{page.title()}':"
                    if isinstance(e, NoPageError):
                        err_log = f"Page '{page.title()}' does not exist."
                        exc_info = False
                        log.debug(err_log, exc_info=exc_info)
                    else:
                        log.error(err_log, exc_info=exc_info)
                        if self.bot and self.log_channel:
                            self.bot.bot.send_message(self.log_channel, f"{err_log} {e}")
                    failed_pages.append(page.title())
                page_cnt = page_cnt + 1
        if len(mod_queue) > 0:
            with open(mod_queue_json_path, "w") as f:
                json.dump([mod.to_dict() for mod in mod_queue], f, indent=2, sort_keys=True)
        log.warning(f"Failed pages: {failed_pages}")
        log.debug(f"Failed pages: {failed_pages}")
        log.debug(f"Missing pages: {missing_pages}")
        log.info(f"Queued pages: {queued_pages}")
        (self.parsed_args.verbosity == Verbosity.NORMAL) and print("")
        self.print_n(f"{page_cnt}/{len(chars)} characters processed. {len(queued_pages)} queued. {pages_noperm} skipped due to perms. {len(failed_pages)} pages produced errors.")

    def process_queue(self):
        mod_queue = None
        shifted_pages = []
        failed_pages = []
        pages_saved = 0
        log.debug("All changes:")
        print("All changes:")
        with open(self.parsed_args.changes_all_file, "r") as f:
            for line in f:
                log.debug(line.strip())
                print(line.strip())
        if not self.parsed_args.non_interactive and input("Enter 'yes' to apply above changes: ").strip().lower() != 'yes':
            raise Exception("Aborting due to user input.")
        with open(mod_queue_json_path, "r") as f:
            mod_queue = json.load(f)
        for mod_dict in mod_queue:
            mod = PageMod.from_dict(mod_dict)
            log.info(f"Processing {mod.title} {mod.title}")
            page = pywikibot.Page(self.site, mod.title)
            page.get(force=True, get_redirect=True)
            pre_path = f"{mod_queue_dir_path}/{mod.title}/pre.wiki"
            post_path = f"{mod_queue_dir_path}/{mod.title}/post.wiki"
            pre_text = None
            post_text = None
            try:
                with open(pre_path, "r") as f:
                    pre_text = f.read()
                if page.text != pre_text:
                    log.warning(f"Page text has changed since queue creation for '{mod.title}', skipping modification.")
                    shifted_pages.append(mod.title)
                    os.remove(pre_path)
                    os.remove(post_path)
                    continue
                with open(post_path, "r") as f:
                    post_text = f.read()
                page.text = post_text
                try:
                    log.info(f"Saving {mod.title} with summary: {mod.summary}")
                    if (self.parsed_args.save_changes):
                        page.save(summary=mod.summary, bot=True, minor=True)
                        post_page = pywikibot.Page(self.site, mod.title)
                        if post_page.text != post_text:
                            raise Exception(f"Post-save text does not match expected text for '{mod.title}' following supposedly successful save.")
                        os.remove(pre_path)
                        os.remove(post_path)
                        pages_saved += 1
                except Exception as e:
                    err_log = f"Error saving page '{mod.title}'"
                    log.error(err_log, exc_info=True)
                    if self.bot and self.log_channel:
                        self.bot.bot.send_message(self.log_channel, f"{err_log} {e}")
                    failed_pages.append(mod.title)
            except Exception as e:
                err_log = f"Error processing page '{mod.title}'"
                log.error(err_log, exc_info=True)
                if self.bot and self.log_channel:
                    self.bot.bot.send_message(self.log_channel, f"{err_log} {e}")
                failed_pages.append(mod.title)
        if len(shifted_pages) > 0:
            log.warning(f"The following pages were skipped due to text changes since queue creation: {shifted_pages}")
            json.dump(shifted_pages, open(f"{mod_queue_dir_path}/shifted_pages.json", "w"), indent=2, sort_keys=True)
        if len(failed_pages) > 0:
            log.warning(f"The following pages failed to update: {failed_pages}")
        if len(shifted_pages) + len(failed_pages) == 0:
            shutil.rmtree(mod_queue_dir_path)
        self.print_n(f"{pages_saved} pages saved. {len(shifted_pages)} pages skipped. {len(failed_pages)} pages failed.")

exit(run_command(SyncCharactersJsonWithWikiPages(sys.argv)))