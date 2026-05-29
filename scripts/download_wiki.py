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

from command import Command, Verbosity, run_command
from discord_logger import DH1
from log_utils import logger as log
from ticker import Ticker

language = "en"
mod_queue_dir_path = pathlib.Path.home() / ".wotwiki" / "mod_queue"
mod_queue_json_path = mod_queue_dir_path / "queue.json"
wiki_name = "wot"

class DownloadWiki(Command):

    def __init__(self, args):
        Command.__init__(self, args)

    def create_arg_parser(self):
        parser = argparse.ArgumentParser(
            description="Download everything on the wiki."
        )
        parser.add_argument(
            "--include-media",
            action="store_true",
            default=False,
            help="If set, the script will include media in the download.")
        parser.add_argument(
            "--latest",
            action="store_true",
            default=False,
            help="""By default, the script downloads the last revision before downloading began in order to obtain a
 snapshot of the wiki at a particular point in time and ignore edits made during the download process. If set, this
 parameter will download the latest version of each page, which is an order of magnitude faster at the cost of
 downloading a snapshot that may not truly represent the wiki at any particular point in time.""")
        parser.add_argument(
            "--out-dir",
            action="store",
            default="./wiki",
            help="Directory to store the downloads.")
        return parser

    def get_namespace_description(self, ns):
        if ns == -2:
            return "Media"
        elif ns == -1:
            return "Special"
        elif ns == 0:
            return "Main"
        elif ns == 1:
            return "Talk"
        elif ns == 2:
            return "User"
        elif ns == 3:
            return "User talk"
        elif ns == 4:
            return "Project"
        elif ns == 5:
            return "Project talk"
        elif ns == 6:
            return "File"
        elif ns == 7:
            return "File talk"
        elif ns == 8:
            return "MediaWiki"
        elif ns == 9:
            return "MediaWiki talk"
        elif ns == 10:
            return "Template"
        elif ns == 11:
            return "Template talk"
        elif ns == 12:
            return "Help"
        elif ns == 13:
            return "Help talk"
        elif ns == 14:
            return "Category"
        elif ns == 15:
            return "Category talk"
        else:
            return f"{ns}"
    
    def run_command(self):
        try:
            self.site = None
            self.preloaded_pages = None
            intro_log = DH1(f"Running downloader for {wiki_name} wiki.")
            log.info(intro_log)
            self.process_args()
            # Set the pywikibot directory to be one level up on the active file path which gives it visibility of the local user-config, password file and families.
            os.environ["PYWIKIBOT_DIR"] = os.path.abspath("../")
            self.site = pywikibot.Site("en", wiki_name)
            self.site.login()
            login_log = f"Logged into wiki {wiki_name} successfully!"
            self.print_n(login_log)
            page_cnt = 0
            failed_pages = []
            ticker = Ticker(10)
            start_time = pywikibot.Timestamp.now()
            for ns in self.site.namespaces:
                nsn = self.get_namespace_description(ns)
                self.print_n(f"Namespace {ns}: {nsn}: ", end="", flush=True)
                if self.parsed_args.include_media != True and int(ns) == -2: # Skip images
                    self.print_n("")
                    self.print_n(f"Skipping namespace {ns}: {nsn}: include_media: {self.parsed_args.include_media}")
                    continue
                if int(ns) == -1: # Skip special
                    self.print_n("")
                    self.print_n(f"Skipping namespace {ns}: {nsn}")
                    continue
                # Skip the Media and Special namespaces
                # if int(ns) >= 0 and int(ns) <= 15:
                #     self.print_n("")
                #     self.print_n(f"Skipping namespace {ns}")
                #     continue
                all_pages_gen = self.site.allpages(namespace=ns)
                self.preloaded_pages = pagegenerators.PreloadingGenerator(all_pages_gen, groupsize=50, quiet=True)
                first_status_log = True
                ticker.restart()
                # TODO Get version of page as it existed when script started runnning.
                for page in self.preloaded_pages:
                    text = page.text
                    if self.parsed_args.latest == False:
                        for rev in page.revisions(starttime=start_time, total=1):
                            text = page.getOldVersion(oldid=rev.revid)
                    if ticker.tick() == True:
                        if not first_status_log and (self.parsed_args.verbosity == Verbosity.NORMAL):
                            print("")
                            self.print_n(f"{page_cnt:5d} pages read. {len(failed_pages):5d} pages produced errors.", end="", flush=True)
                        first_status_log = False
                        sleep(ticker.period - 5)
                    (self.parsed_args.verbosity == Verbosity.NORMAL) and print(".", end="", flush=True)
                    log.debug("Processing page: %s", page)
                    try:
                        page.get(get_redirect=True)
                        os.makedirs(mod_queue_dir_path, exist_ok=True)
                        filename = page.title()
                        ext = ".wiki"
                        if re.match(r"^Module\:[^/]+$", page.title()):
                            ext = ".lua"
                        elif re.match(r".*\.json$", page.title()):
                            filename = re.sub(r"\.json$", "", filename)
                            ext = ".json"
                        filename = self.sanitize_str_for_filename(filename)
                        page_path = f"{self.parsed_args.out_dir}/{filename}{ext}"
                        os.makedirs(os.path.dirname(page_path), exist_ok=True)
                        if pathlib.Path(page_path).exists():
                            raise Exception(f"Page path {page_path} already exists, skipping page '{page.title()}'.")
                        with open(page_path, "w") as f:
                            f.write(text)
                    except Exception as e:
                        err_log = f"Error processing page '{page.title()}':"
                        log.error(err_log, exc_info=True)
                        failed_pages.append(page.title())
                    page_cnt = page_cnt + 1
                log.warning("Failed pages: %r", failed_pages)
                (self.parsed_args.verbosity == Verbosity.NORMAL) and print("")
                self.print_n(f"{page_cnt} pages read. {len(failed_pages)} pages produced errors.")
        except Exception as e:
            log.error(e, exc_info=True)
            raise
        return 0

    def process_args(self):
        log.debug("Processing arguments.")

    def sanitize_str_for_filename(self, s):
        s = re.sub(r"[^a-zA-Z0-9_\-\\\/ \'\:\.]", "_", s)
        return s

exit(run_command(DownloadWiki(sys.argv)))