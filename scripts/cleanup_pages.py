# This script requires pywikibot to be properly configured with a families/wot_family.py and a user file.
# Example user file for a bot named "androlf-bot" for a user named "androlf":
# Filename: Androlf@androlf-bot_password.py
# Contents:
#('Androlf', BotPassword('androlf-bot', 'putThePasswordHere'))

import argparse
import json
import sys
import log_utils
import os
import shutil
import time
import pywikibot
import re
import urllib.parse
import utils
from command import Command, run_command
from log_utils import logger as log
from page_mod import PageMod
from pathlib import Path
from pywikibot import pagegenerators

wiki_name = "wot"
language = "en"

hard_ww_link_re = r"\[http(s){0,1}://(www\.){0,1}wot\.(fandom|wikia)\.com\/wiki\/([^ ]+) ([^\]]+)\]"
mod_queue_dir_path = "mod_queue"
mod_queue_json_path = mod_queue_dir_path + "/queue.json"

class CleanupPages(Command):

    def __init__(self, args):
        Command.__init__(self, args)

    def create_arg_parser(self):
        parser = argparse.ArgumentParser(
            description="Run the cleanup checklist against wotwiki's main namespace."
        )
        parser.add_argument(
            "--save-changes",
            action="store_true",
            default=False,
            help="If not set, the script will not save changes to the wiki.")
        return parser

    def run_command(self):
        self.site = None
        self.preloaded_pages = None
        self.page_group_size = 50
        self.dry_run = True
        log.info(f"Running page cleanup for {wiki_name} wiki.")
        self.process_args()
        if not self.dry_run:
            log.warning(f"self.dry_run is {self.dry_run}, this run {self.dry_run and 'WILL NOT' or 'MAY'} save changes to the wiki!")
        # Set the pywikibot directory to be one level up on the active file path which gives it visibility of the local user-config, password file and families.
        os.environ["PYWIKIBOT_DIR"] = os.path.abspath("../")
        # print("env: " + os.environ["PYWIKIBOT_DIR"])
        # wiki_name comes from variables above, i.e. domo.fandom.com this wiki_name variable would be "domo"
        self.site = pywikibot.Site("en", "wot")
        self.site.login()
        self.print_n("Logged in successfully!")
        all_pages_gen = self.site.allpages(namespace=0)
        self.preloaded_pages = pagegenerators.PreloadingGenerator(all_pages_gen, groupsize=self.page_group_size)
        # self.preloaded_pages = [ pywikibot.Page(site, p) for p in [ "Author unknown", "Mallard's Hill" ] ]
        # This is deliberately not an if/else
        if not Path(mod_queue_dir_path).is_dir():
            self.create_queue()
        if Path(mod_queue_dir_path).is_dir():
            self.process_queue()
        return 0

    def process_args(self):
        log.debug("Processing arguments.")
        if self.mParsedArgs.save_changes:
            self.dry_run = False

    def create_queue(self):
        mod_queue = []
        still_dirty = []
        page_num = 0
        page_cnt = 0
        page_id = 1
        pages_modified = 0
        pages_noperm = 0
        with open(f"changes-all.diff", "w") as all_changes_file, open(f"changes.diff", "w") as changes_file:
            for page in self.preloaded_pages:
                log.debug("Processing page: %s", page.title())
                page.get(get_redirect=True)
                pre_text = page.text
                match = True
                while (match):
                    match = re.search(hard_ww_link_re, page.text, re.IGNORECASE | re.MULTILINE)
                    if not match:
                        break
                    target = re.sub(r"_", " ", urllib.parse.unquote(match.group(4)))
                    display = match.group(5)
                    page.text = re.sub(hard_ww_link_re, ((target == display) and r"[[\5]]" or r"[[\4|\5]]"), page.text, 1, flags=re.IGNORECASE | re.MULTILINE)
                if pre_text != page.text:
                    mod = PageMod(page_id, urllib.parse.unquote(page.title()))
                    mod_path = f"{mod_queue_dir_path}/{mod.title}"
                    os.makedirs(mod_queue_dir_path, exist_ok=True)
                    pre_path = f"{mod_path}-pre.wiki"
                    post_path = f"{mod_path}-post.wiki"
                    with open(pre_path, "w") as f:
                        f.write(pre_text)
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
                    all_changes_file.write(f"{page.title()}\n")
                    all_changes_file.write(subp.stdout)
                    all_changes_file.write("\n")
                    if (page.botMayEdit()):
                        log.info(f"{page.title()} needs updating, queuing.")
                        mod_queue.append(mod)
                        page_id += 1
                        log.info(f"{page.title()} queued.")
                        changes_file.write(f"{page.title()}\n")
                        changes_file.write(subp.stdout)
                        changes_file.write("\n")
                    else:
                        page.text = pre_text
                        log.warning(f"{page.title()} needs updating but bot is not allowed to edit it.")
                        pages_noperm += 1
                    pages_modified += 1
                match = re.search(r".{0,50}wot\.(fandom|wikia).{0,50}", page.text, re.IGNORECASE | re.MULTILINE)
                if (match):
                    log.warning(f"{page.title()} seems to contain a hard-coded wotwiki link even after cleanup: {match}")
                    still_dirty.append(page.title())
                page_num = (page_num % self.page_group_size) + 1
                page_cnt = page_cnt + 1
        if len(mod_queue) > 0:
            with open(mod_queue_json_path, "w") as f:
                json.dump([mod.to_dict() for mod in mod_queue], f, indent=2, sort_keys=True)
        log.info(f"Pages that will still contain hard-coded wotwiki links after changes are applied: {still_dirty}")
        log.info(f"{page_cnt} pages read. {pages_modified} queued. {pages_noperm} skipped due to perms.")

    def process_queue(self):
        mod_queue = None
        shifted_pages = []
        failed_pages = []
        pages_saved = 0
        log.debug("All changes:")
        print("All changes:")
        with open(f"changes-all.diff", "r") as f:
            for line in f:
                log.debug(line.strip())
                print(line.strip())
        if input("Enter 'yes' to apply above changes: ").strip().lower() != 'yes':
            raise Exception("Aborting due to user input.")
        with open(mod_queue_json_path, "r") as f:
            mod_queue = json.load(f)
        for mod_dict in mod_queue:
            mod = PageMod.from_dict(mod_dict)
            log.info(f"Processing {mod.title}")
            page = pywikibot.Page(self.site, mod.title)
            page.get(force=True, get_redirect=True)
            pre_path = f"{mod_queue_dir_path}/{mod.title}-pre.wiki"
            post_path = f"{mod_queue_dir_path}/{mod.title}-post.wiki"
            try:
                with open(pre_path, "r") as f:
                    pre_text = f.read()
                with open(post_path, "r") as f:
                    post_text = f.read()
                if page.text != pre_text:
                    log.warning(f"Page text has changed since queue creation for {mod.title}, skipping modification.")
                    shifted_pages.append(mod.title)
                    os.remove(pre_path)
                    os.remove(post_path)
                    continue
                page.text = post_text
                try:
                    if (not self.dry_run):
                        page.save(
                            summary="Fix hard-coded wotwiki links",
                            bot=True,
                            minor=True
                        )
                        time.sleep(1) # Avoid ratelimiting
                    pages_saved += 1
                    os.remove(pre_path)
                    os.remove(post_path)
                except Exception as e:
                    log.error(f"Error saving page {mod.title}: {e}")
                    failed_pages.append(mod.title)
            except Exception as e:
                log.error(f"Error processing page {mod.title}: {e}")
                shifted_pages.append(mod.title)
        if len(shifted_pages) > 0:
            log.warning(f"The following pages were skipped due to text changes since queue creation: {shifted_pages}")
            json.dump(shifted_pages, open(f"{mod_queue_dir_path}/shifted_pages.json", "w"), indent=2, sort_keys=True)
            os.remove(mod_queue_json_path)
            log.warning(f"The following pages failed to update: {failed_pages}")
        else:
            shutil.rmtree(mod_queue_dir_path)
        log.info(f"{pages_saved} pages saved. {len(shifted_pages)} pages skipped. {len(failed_pages)} pages failed.")

exit(run_command(CleanupPages(sys.argv)))