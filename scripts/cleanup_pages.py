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
from page_mod import PageMod, PageModifier
from pathlib import Path
from pywikibot import pagegenerators, textlib

language = "en"
mod_queue_dir_path = "mod_queue"
mod_queue_json_path = mod_queue_dir_path + "/queue.json"
wiki_name = "wot"

spelling_re_modifiers_exceptions = [ 'math', 'nowiki', 'interwiki', "invoke", "property" ]
spelling_re_modifiers = [
    [ r"Moraine", r"Moiraine", False ],
    [ r"Perin", r"Perrin", False ],
    [ r"([Ss])hiled", r"\1hield", False ],
    [ r"Turok", r"Turak", False ],
]
regex_modifiers_exceptions = [ 'comment', 'math', 'nowiki', 'template', 'hyperlink', 'interwiki', 'category', 'file', "invoke", "property" ]
regex_modifiers = [
    [ "Wolf dream is two words.", r"(wolf)(dream)", r"\1 \2", 0, True ],
    [ "Dreamspike is one word.", r"(dream)\sspike", r"\1spike", 0, True ],
    # Capitalize Shadowspawn, Darkfriend, Forsaken, Aes Sedai, Myrdraal, (NOT Fade), Trolloc
    # [ "Capitalize Asha'man.", r"asha'man", r"Asha'man", 0, False ], # Needs to be tested
    # [ "Capitalize TAR.", r"tel'aran'rhiod", r"Tel'aran'rhiod", 0, True ], # Needs to be tested
    # [ "Lowercase sul'dam.", r"([^\.\!\?]\s|\[)Sul'dam", r"\1sul'dam", 0, False ], # Needs to be tested
    # [ "Lowercase damane.", r"([^\.\!\?]\s|\[)Damane", r"\1damane", 0, False ], # Needs to be tested
    # [ "Link AB dates.", r"([^\[])(\d{1,4}) AB([^A-Za-z\]\|])([^\]])", r"\1{{ab|\2}}\3\4", 0, False ], # Needs to be tested
    # [ "Link NE dates.", r"([^\[])(\d{1,4}) NE([^A-Za-z\]\|])([^\]])", r"\1{{ne|\2}}\3\4", 0, False ], # Needs to be tested
    # [ "Link FY dates.", r"([^A-Za-z\[]])FY (\d{1,4})([^\|\]])", r"\1{{fy|\2}}\3", 0, False ], # Needs to be tested
]
# italicize_modifiers = [ "Tel'aran'rhiod", "sul'dam", "damane", "ter'angreal", "sa'angreal", "angreal", "grolm", "gholam" ] # Needs to be tested, particulary with respect to words being in filenames and link display text.

class AbsoluteWikiLinkModifier(PageModifier):
    pattern = r"\[https{0,1}://(www\.){0,1}wot\.(fandom|wikia)\.com\/wiki\/([^ ]+) ([^\]]+)\]"

    def __init__(self):
        super().__init__("Fix hard-coded wotwiki links.")

    def process_page_logic(self, page):
        match = True
        while (match):
            match = re.search(AbsoluteWikiLinkModifier.pattern, page.text, re.IGNORECASE | re.MULTILINE)
            if not match:
                break
            target = re.sub(r"_", " ", urllib.parse.unquote(match.group(4)))
            display = match.group(5)
            page.text = re.sub(AbsoluteWikiLinkModifier.pattern, ((target == display) and r"[[\5]]" or r"[[\4|\5]]"), page.text, 1, flags = re.IGNORECASE | re.MULTILINE)

modifiers = [ AbsoluteWikiLinkModifier() ]

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
        log.info(f"Running page cleanup for {wiki_name} wiki.")
        self.process_args()
        if not self.parsed_args.save_changes:
            log.warning(f"self.parsed_args.save_changes is {self.parsed_args.save_changes}, this run {self.parsed_args.save_changes and 'WILL NOT' or 'MAY'} save changes to the wiki!")
        # Set the pywikibot directory to be one level up on the active file path which gives it visibility of the local user-config, password file and families.
        os.environ["PYWIKIBOT_DIR"] = os.path.abspath("../")
        # print("env: " + os.environ["PYWIKIBOT_DIR"])
        # wiki_name comes from variables above, i.e. domo.fandom.com this wiki_name variable would be "domo"
        self.site = pywikibot.Site("en", "wot")
        self.site.login()
        self.print_n("Logged in successfully!")
        all_pages_gen = self.site.allpages(namespace=0)
        self.preloaded_pages = pagegenerators.PreloadingGenerator(all_pages_gen, groupsize=50, quiet=True)
        # self.preloaded_pages = [ pywikibot.Page(self.site, p) for p in [ "Al'Dai", "Colly Garren", "Jared Aydaer", "Teven Marwin", "The Shadow Rising/Chapter 31" ] ]
        # This is deliberately not an if/else
        if not Path(mod_queue_dir_path).is_dir():
            self.create_queue()
        if Path(mod_queue_dir_path).is_dir():
            self.process_queue()
        return 0

    def process_args(self):
        log.debug("Processing arguments.")

    def create_queue(self):
        mod_queue = []
        still_dirty = []
        page_cnt = 0
        page_id = 1
        pages_modified = 0
        pages_noperm = 0
        with open(f"changes-all.diff", "w") as all_changes_file, open(f"changes.diff", "w") as changes_file:
            for page in self.preloaded_pages:
                if (page_cnt % 100 == 0 and page_cnt > 0):
                    self.print_n(f"{page_cnt} pages read.")
                log.debug("Processing page: %s", page.title())
                page.get(get_redirect=True)
                pre_text = page.text
                mod = PageMod(page_id, urllib.parse.unquote(page.title()))
                for modifier in spelling_re_modifiers:
                    pt = page.text
                    page.text = textlib.replaceExcept(text=page.text, old=modifier[0], new=modifier[1], exceptions=spelling_re_modifiers_exceptions, count=0, caseInsensitive=modifier[2], site=self.site)
                    # page.text = re.sub(modifier[0], modifier[1], page.text, 0, flags = modifier[2])
                    if (pt != page.text):
                        if (len(mod.summary) > 0):
                            mod.summary = mod.summary + " "
                        mod.summary = mod.summary + "Spelling."
                # for modifier in italicize_modifiers:
                #     pt = page.text
                #     page.text = textlib.replaceExcept(text=page.text, old=r"([^a-z'\[\:])('{0,2})(" + modifier + r")\2([^a-z'\]])", new=r"\1''\3''\4", exceptions=regex_modifiers_exceptions, count=0, caseInsensitive=True, site=self.site)
                #     # page.text = re.sub(r"([^a-z'\[\:])('{0,2})(" + modifier + r")\2([^a-z'\]])", r"\1''\3''\4", page.text, 0, re.IGNORECASE | re.MULTILINE)
                #     if (pt != page.text):
                #         if (len(mod.summary) > 0):
                #             mod.summary = mod.summary + " "
                #         mod.summary = mod.summary + "Italicize " + modifier + "."
                for modifier in regex_modifiers:
                    pt = page.text
                    page.text = textlib.replaceExcept(text=page.text, old=modifier[1], new=modifier[2], exceptions=regex_modifiers_exceptions, count=modifier[3], caseInsensitive=modifier[4], site=self.site)
                    # page.text = re.sub(modifier[1], modifier[2], page.text, modifier[3], flags = modifier[4])
                    if (pt != page.text):
                        if (len(mod.summary) > 0):
                            mod.summary = mod.summary + " "
                        mod.summary = mod.summary + modifier[0]
                for modifier in modifiers:
                    if (modifier.process_page(page)):
                        if (len(mod.summary) > 0):
                            mod.summary = mod.summary + " "
                        mod.summary = mod.summary + modifier.summary
                if pre_text != page.text:
                    mod_path = f"{mod_queue_dir_path}/{mod.title}"
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
                    if (page.botMayEdit()):
                        log.info(f"{page.title()} needs updating, queuing. Summary: {mod.summary}")
                        mod_queue.append(mod)
                        page_id += 1
                        changes_file.write(subp.stdout)
                        changes_file.write("\n")
                    else:
                        page.text = pre_text
                        log.warning(f"{page.title()} needs updating but bot is not allowed to edit it.")
                        pages_noperm += 1
                    pages_modified += 1
                match = re.search(r".{0,50}wot\.(fandom|wikia).{0,50}", page.text, re.IGNORECASE | re.MULTILINE)
                if (match):
                    log.warning(f"Page '{page.title()}' seems to contain a hard-coded wotwiki link even after cleanup: {match}")
                    still_dirty.append(page.title())
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
                        time.sleep(1) # Avoid ratelimiting
                        post_page = pywikibot.Page(self.site, mod.title)
                        if post_page.text != post_text:
                            raise Exception(f"Post-save text does not match expected text for '{mod.title}' following supposedly successful save.")
                    pages_saved += 1
                    os.remove(pre_path)
                    os.remove(post_path)
                except Exception as e:
                    log.error(f"Error saving page {mod.title}: {e}")
                    failed_pages.append(mod.title)
            except Exception as e:
                log.error(f"Error processing page {mod.title}: {e}")
                failed_pages.append(mod.title)
        if len(shifted_pages) > 0:
            log.warning(f"The following pages were skipped due to text changes since queue creation: {shifted_pages}")
            json.dump(shifted_pages, open(f"{mod_queue_dir_path}/shifted_pages.json", "w"), indent=2, sort_keys=True)
        if len(failed_pages) > 0:
            log.warning(f"The following pages failed to update: {failed_pages}")
        if len(shifted_pages) + len(failed_pages) == 0:
            shutil.rmtree(mod_queue_dir_path)
        self.print_n(f"{pages_saved} pages saved. {len(shifted_pages)} pages skipped. {len(failed_pages)} pages failed.")

exit(run_command(CleanupPages(sys.argv)))