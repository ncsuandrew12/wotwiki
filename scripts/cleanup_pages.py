# This script requires pywikibot to be properly configured with a families/wot_family.py and a user file.
# Example user file for a bot named "androlf-bot" for a user named "androlf":
# Filename: Androlf@androlf-bot_password.py
# Contents:
#('Androlf', BotPassword('androlf-bot', 'putThePasswordHere'))

import argparse
from fileinput import filename
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

# TODO:
# e.g. [[Gareth Bryne|Gareth's]] -> [[Gareth Bryne|Gareth]]'s
# ' ' (U+00a0) -> ' '
# Determine way to exclude specific pages or sections from specific types changes. In particular, transcriptions of
# textual content. E.g. Source pages and Beasts of the Wheel of Time should allow changes to link wikitext that results
# in the same actual text (e.g. [[Abc|Abcs]] -> [[Abc]]s), but shouldn't allow changes that modify the actual text (e.g.
# robert jordan -> Robert Jordan)

# TODO:
# Basic word misspellings need to exclude pronunciation strings
# Incorporate all feasible common misspellings: https://wot.fandom.com/wiki/Wotwiki:List_of_common_misspellings
#   Non-mundane entries from A-G have already been added.
modifiers_lookbehind = r"(?<!image=)(?<!image\s=)(?<!image\s=\s)(?<!image=\s)(?<!File:)(?<!\w)"
modifier_makelc_lookbehind = r"(?<![.!?]\s)(?<![*#])(?<![*#]\[\[)(?<![*#]\s\[\[)"
spelling_re_modifiers = [
    [ "a'dam", modifiers_lookbehind + r"adam(?![A-Za-rt-z])", r"a'dam", 0 ],
    [ "Aiel", r"(\W)[Aa]eil", r"\1Aiel", 0 ],
    [ "Amadician", r"Amadican", r"Amadician", re.IGNORECASE ],
    [ "Andoran", r"(\W)Andorian", r"\1Andoran", re.IGNORECASE ],
    [ "Artur Hawkwing", r"Arthur Hawkw{0,1}ing", r"Artur Hawkwing", re.IGNORECASE ],
    [ "Asha'man", r"(Ashamen)|(Asha'men)", r"Asha'man", re.IGNORECASE ],
    [ "Asha'man (omitted apostrophe)", modifiers_lookbehind + r"Ashaman", r"Asha'man", re.IGNORECASE ],
    [ "Atha'an Miere", r"Atha{1,2}n\smiere", r"Atha'an Miere", re.IGNORECASE ],
    [ "Cairhien", r"(Carhien)|(Cairhein)", r"Cairhien", re.IGNORECASE ],
    [ "Cairhienin", r"(carhienen)|(Cairheinen)|(Cairhienen)", r"Cairhienin", re.IGNORECASE ],
    [ "Callandor", r"Calandor", r"Callandor", re.IGNORECASE ],
    [ "dareis", r"(?<!\w)([Dd])aries(?!\w)", r"\1areis", 0 ],
    [ "Draghkar", r"(?<!\w)([Dd])rakkar", r"\1raghkar", 0 ],
    [ "dreamspike", r"(dream)\s+spike", r"\1spike", re.IGNORECASE ],
    [ "dreamspike (capitalization)", modifier_makelc_lookbehind + r"dreamspike", r"dreamspike", re.IGNORECASE ],
    [ "Ghealdanin", r"(?<!\w)ghealdanen", r"Ghealdanin", re.IGNORECASE ],
    [ "Ghenjei", r"(?<!\w)(genjei)|(ghenji)|(genji)", r"Ghenjei", re.IGNORECASE ],
    [ "gholam", r"(?<!\w)([Gg])ohlam", r"\1holam", 0 ],
    [ "Graendal", r"(?<!\w)(grendahl)|(grendahl)", r"Graendal", re.IGNORECASE ],
    [ "Gray Ajah", r"(?<!\w)grey ajah", r"Gray Ajah", re.IGNORECASE ],
    [ "Gray Man/Men", r"(?<!\w)([Gg])rey (M[ae]n)", r"\1ray \2", 0 ],
    [ "Kandorian", r"(?<!\w)Kandoran", r"Kandorian", re.IGNORECASE ],
    [ "Moiraine", r"(?<!\[\[es\:)Moraine", r"Moiraine", 0 ],
    [ "Perrin", r"Perin", r"Perrin", 0 ],
    [ "shield", r"([Ss])hiled", r"\1hield", 0 ],
    [ "siege", r"(?<!\w)seige(?!\w)", r"siege", 0 ],
    [ "the", r"(?<!\w)(?<!-)teh(?!\w)", r"the", 0 ],
    [ "Turak", r"Turok", r"Turak", 0 ],
    [ "wolf dream", r"(wolf)(dream)", r"\1 \2", re.IGNORECASE ],
    # The extra look behind and look ahead help avoid references to the Perrin's Wolf Dreams page and the Wolf Dreams chapter.
    [ "wolf dream (capitalization)", modifier_makelc_lookbehind + r"(?<!\[\[Perrin's )wolf dream", r"wolf dream", re.IGNORECASE ], # Needs to be tested
    # [ "Capitalize TAR.", r"tel'aran'rhiod", r"Tel'aran'rhiod", 0, re.IGNORECASE ], # Needs to be tested
    # [ "Lowercase sul'dam.", r"([^\.\!\?]\s|\[)Sul'dam", r"\1sul'dam", 0, re.IGNORECASE ], # Needs to be tested
    # [ "Lowercase damane.", r"([^\.\!\?]\s|\[)Damane", r"\1damane", 0, re.IGNORECASE ], # Needs to be tested
]
regex_modifiers = [
    # [ "Companion footnote style.", r"\{\{ref|\{\{twotc\}\},\s*([A-Za-z0-9][^\},]*)(\|[^\}]+){0,1}\}\}", r"\{\{ref/book\|twotc\|\1\2\}\}", 0, re.IGNORECASE ], # Needs to be tested
    # [ "Converted raw ref tag to template.", r"\<ref\>([^<]+)\</ref\>", r"{{ref|\1}}", 0, re.IGNORECASE ], # Needs to be tested
    # [ "Converted raw ref tag to template.", r"\<ref name=(\"{0,1})([^\"]+)\1\>([^<]+)\</ref\>", r"{{ref|\3|\2}}", 0, re.IGNORECASE ], # Needs to be tested
    # [ "Fix section link Trolloc#Social_Structure -> Trolloc#Trolloc_bands.", r"\[\[Trolloc#Social_Structure\]\]", r"\[\[Trolloc#Trolloc_bands\]\]", 0, re.IGNORECASE ], # Needs to be tested
    # [ "Unnecessary link customization.", r"\[\[([^\]\|]+)\|\1((\'s)|s|(es)){0,1}\]\]", r"[[\1]]\2", 0, re.IGNORECASE ], # Changes are massive. Use of this should wait for a massive change set that includes more valuable changes.
    [ "Link AB dates.", r"([^\[])(\d{1,4}) AB([^A-Za-z\]\|])([^\]])", r"\1{{ab|\2}}\3\4", 0, re.IGNORECASE ], # Needs to be tested
    [ "Link FY dates.", r"([^A-Za-z\[]])FY (\d{1,4})([^\|\]])", r"\1{{fy|\2}}\3", 0, re.IGNORECASE ], # Needs to be tested
    [ "Link NE dates.", r"([^\[])(\d{1,4}) NE([^A-Za-z\]\|])([^\]])", r"\1{{ne|\2}}\3\4", 0, re.IGNORECASE ], # Needs to be tested
    [ "Fix Wolf Dreams chapter link", r"(\[\[)wolf dreams([\|\]])", r"\1Wolf Dreams\2", 0, re.IGNORECASE ], # Needs to be tested
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

class OnePowerStrengthLinkModifier(PageModifier):
    patternParen = r"(\d+)\((\+{0,1})(\d+)\)"
    patternPlusPlus = r"\+\+(\d+)"

    def __init__(self):
        super().__init__("Convert raw One Power strength text to Opsl template.")

    def process_page_logic(self, page):
        match = True
        while (match):
            match = re.search(OnePowerStrengthLinkModifier.patternParen, page.text, re.IGNORECASE | re.MULTILINE)
            if match:
                newSystem = int(match.group(1))
                plus = match.group(2)
                oldSystem = int(match.group(3))
                oldSystemConverted = oldSystem + 12
                if (plus == "+"):
                    oldSystemConverted = 13 - oldSystem
                if (newSystem != oldSystemConverted):
                    if (plus == "" and newSystem == 13 - oldSystem):
                        log.warning(f"Page '{page.title()}' seems to contain a One Power strength ({match.group(1)}({match.group(2)}{match.group(3)})) that omits the + when denoting the old system strength. Will fix.")
                    elif (plus == "+" and newSystem == oldSystem + 12):
                        log.warning(f"Page '{page.title()}' seems to contain a One Power strength ({match.group(1)}({match.group(2)}{match.group(3)})) that mistakenly includes the + when denoting the old system strength. Will fix.")
                    else:
                        raise Exception(f"Invalid One Power strength found in page {page.title()}: {match.group(1)}({match.group(2)}{match.group(3)}). Old system rating ({oldSystem}) converts to {oldSystemConverted}, but new system is {newSystem}.")
                page.text = re.sub(
                    OnePowerStrengthLinkModifier.patternParen,
                    f"{{{{opsl|{newSystem + 6}}}}}",
                    page.text, 1, flags = re.IGNORECASE | re.MULTILINE)
                continue
            match = re.search(OnePowerStrengthLinkModifier.patternPlusPlus, page.text, re.IGNORECASE | re.MULTILINE)
            if match:
                page.text = re.sub(
                    OnePowerStrengthLinkModifier.patternPlusPlus,
                    f"{{{{opsl|{int(match.group(1))}}}}}",
                    page.text, 1, flags = re.IGNORECASE | re.MULTILINE)
                continue

modifiers = [
    AbsoluteWikiLinkModifier(),
    OnePowerStrengthLinkModifier()
]

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
        # self.preloaded_pages = [ pywikibot.Page(self.site, p) for p in [ "Known Contradictions and Points of Ambiguity" ] ]
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
        pages_noperm = 0
        failed_pages = []
        queued_pages = []
        with open(f"changes-all.diff", "w") as all_changes_file, open(f"changes.diff", "w") as changes_file:
            for page in self.preloaded_pages:
                if (page_cnt % 100 == 0 and page_cnt > 0):
                    self.print_n(f"{page_cnt} pages read. {len(queued_pages)} queued. {pages_noperm} skipped due to perms. {len(failed_pages)} pages produced errors.")
                log.debug("Processing page: %s", page.title())
                try:
                    page.get(get_redirect=True)
                    pre_text = page.text
                    mod = PageMod(page_id, urllib.parse.unquote(page.title()))
                    for modifier in spelling_re_modifiers:
                        premod_text = page.text
                        page.text = re.sub(modifier[1], modifier[2], page.text, 0, flags = modifier[3])
                        if (premod_text != page.text):
                            log.debug(f"Applied spelling regex modifier to page '{page.title()}': {modifier}.")
                            mod.summary.append(f"Spelling ({modifier[0]}).")
                    # for modifier in italicize_modifiers:
                    #     pt = page.text
                    #     page.text = textlib.replaceExcept(text=page.text, old=r"([^a-z'\[\:])('{0,2})(" + modifier + r")\2([^a-z'\]])", new=r"\1''\3''\4", exceptions=regex_modifiers_exceptions, count=0, caseInsensitive=True, site=self.site)
                    #     # page.text = re.sub(r"([^a-z'\[\:])('{0,2})(" + modifier + r")\2([^a-z'\]])", r"\1''\3''\4", page.text, 0, re.IGNORECASE | re.MULTILINE)
                    #     if (pt != page.text):
                    #        log.debug(f"Applied italicization modifier to page '{page.title()}': {modifier}.")
                    #        mod.summary.append(f"Italicize.")
                    for modifier in regex_modifiers:
                        premod_text = page.text
                        page.text = re.sub(modifier[1], modifier[2], page.text, modifier[3], flags = modifier[4])
                        if (premod_text != page.text):
                            log.debug(f"Applied regex modifier to page '{page.title()}': {modifier}.")
                            mod.summary.append(modifier[0])
                    for modifier in modifiers:
                        if (modifier.process_page(page)):
                            log.debug(f"Applied modifier to page '{page.title()}': {modifier}.")
                            mod.summary.append(modifier.summary)
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
                        deduped_summary = []
                        for line in mod.summary:
                            if line not in deduped_summary:
                                deduped_summary.append(line)
                        mod.summary = " ".join(deduped_summary)
                        if (page.botMayEdit()):
                            log.info(f"Page '{page.title()}' needs update, queuing. Summary: {mod.summary}")
                            mod_queue.append(mod)
                            queued_pages.append(mod.title)
                            page_id += 1
                            changes_file.write(subp.stdout)
                            changes_file.write("\n")
                        else:
                            page.text = pre_text
                            log.warning(f"Page '{page.title()}' needs update but bot is not allowed to edit it. Summary: {mod.summary}")
                            pages_noperm += 1
                    match = re.search(r"\/\/wot\.(fandom|wikia)", page.text, re.IGNORECASE | re.MULTILINE)
                    if (match):
                        log.warning(f"Page '{page.title()}' seems to contain a hard-coded wotwiki link even after cleanup: {match}:   \"{page.text[max(0, match.start()-20):min(len(page.text), match.end()+20)]}\"")
                        still_dirty.append(page.title())
                except Exception as e:
                    log.error(f"Error processing page '{page.title()}':", exc_info=True)
                    failed_pages.append(page.title())
                page_cnt = page_cnt + 1
        if len(mod_queue) > 0:
            with open(mod_queue_json_path, "w") as f:
                json.dump([mod.to_dict() for mod in mod_queue], f, indent=2, sort_keys=True)
        log.info(f"Pages that will still contain hard-coded wotwiki links after changes are applied: {still_dirty}")
        log.warning(f"Failed pages: {failed_pages}")
        log.debug(f"Failed pages: {failed_pages}")
        log.info(f"Queued pages: {queued_pages}")
        self.print_n(f"{page_cnt} pages read. {len(queued_pages)} queued. {pages_noperm} skipped due to perms. {len(failed_pages)} pages produced errors.")

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
                    log.error(f"Error saving page '{mod.title}'", exc_info=True)
                    failed_pages.append(mod.title)
            except Exception as e:
                log.error(f"Error processing page '{mod.title}':", exc_info=True)
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