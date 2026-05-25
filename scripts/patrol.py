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
from pathlib import Path
from pywikibot import pagegenerators

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

# TODO:
# e.g. [[Gareth Bryne|Gareth's]] -> [[Gareth Bryne|Gareth]]'s
# Determine way to exclude specific pages or sections from specific types changes. In particular, transcriptions of
# textual content. E.g. Source pages and Beasts of the Wheel of Time should allow changes to link wikitext that results
# in the same actual text (e.g. [[Abc|Abcs]] -> [[Abc]]s), but shouldn't allow changes that modify the actual text (e.g.
# robert jordan -> Robert Jordan)

# TODO:
# Basic word misspellings need to exclude pronunciation strings
# Incorporate all feasible common misspellings: https://wot.fandom.com/wiki/Wotwiki:List_of_common_misspellings
#   Non-mundane entries from A-G have already been added.
# Flag pages that have the Wotwiki featured article category (or otherwise might be targetd by DPL), but use {{PAGENAME}}
# Do more icon stuff. See Template:Featuredicon
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
    [ "wolf dream (capitalization)", modifier_makelc_lookbehind + r"(?<!\[\[Perrin's )(?<!Chapter 9\|)(?<!DISPLAYTITLE:\'\')wolf dream", r"wolf dream", re.IGNORECASE ], # Needs to be tested
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
    # [ "Link AB dates (range).", r"([^\[])(\d{1,4})(\s*-\s*)(\d{1,4}) AB([^A-Za-z\]\|])([^\]])", r"\1{{ab|\2}}\3{{ab|\4}}\5\6", 0, re.IGNORECASE ], # Needs to be tested
    [ "Link AB dates.", r"([^\[\d])(\d{1,4}) AB([^A-Za-z\]\|])([^\]])", r"\1{{ab|\2}}\3\4", 0, re.IGNORECASE ], # Needs to be tested
    # [ "Link FY dates (range).", r"([^A-Za-z\[]])FY (\d{1,4})(\s*-\s*)(\d{1,4})([^\|\]])", r"\1{{fy|\2}}\3{{fy|\4}}\5", 0, re.IGNORECASE ], # Needs to be tested
    [ "Link FY dates.", r"([^A-Za-z\[]])FY (\d{1,4})([^\|\]])", r"\1{{fy|\2}}\3", 0, re.IGNORECASE ], # Needs to be tested
    # TODO Enhance to handle (or ignore) specific days (e.g. 999-9-14 NE)
    # [ "Link NE dates (range).", r"([^\[])(\d{1,4})(\s*-\s*)(\d{1,4}) NE([^A-Za-z\]\|])([^\]])", r"\1{{ne|\2}}\3{{ne|\4}}\5\6", 0, re.IGNORECASE ],
    # [ "Link NE dates.", r"([^\[\d])(\d{1,4}) NE([^A-Za-z\]\|])([^\]])", r"\1{{ne|\2}}\3\4", 0, re.IGNORECASE ],
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
            target = re.sub(r"_", " ", urllib.parse.unquote(match.group(3)))
            display = match.group(4)
            page.text = re.sub(AbsoluteWikiLinkModifier.pattern, ((target == display) and r"[[\4]]" or r"[[\3|\4]]"), page.text, 1, flags = re.IGNORECASE | re.MULTILINE)

class OnePowerStrengthLinkModifier(PageModifier):
    patternParen = r"(\d+)\((\+{0,1})(\d+)\)"
    patternPlusPlus = r"\+\+(\d+)"
    allowBadStructuredOps = [ 'Magla Daronos', 'Sorilea', 'Strength in the One Power among Aes Sedai' ]

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
                    elif page.title() in OnePowerStrengthLinkModifier.allowBadStructuredOps:
                        log.warning(f"Page '{page.title()}' seems to contain a One Power strength ({match.group(1)}({match.group(2)}{match.group(3)})) that looks invalid.  Old system rating ({oldSystem}) converts to {oldSystemConverted}, but new system is {newSystem}.")
                        page.text = re.sub(
                            OnePowerStrengthLinkModifier.patternParen,
                            f"[[Strength in the One Power rankings#rank{newSystem + 6}|{match.group(1)}]]([[Strength in the One Power rankings#rank{oldSystemConverted + 6}|{match.group(2)}{match.group(3)}]])",
                            page.text, 1, flags = re.IGNORECASE | re.MULTILINE)
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

class Patrol(Command):

    def __init__(self, args):
        Command.__init__(self, args)
        self.bot = None
        self.log_channel = None

    def create_arg_parser(self):
        parser = argparse.ArgumentParser(
            description="Run the cleanup checklist against wotwiki's main namespace."
        )
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
            default="(bot patrol) ",
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
        if q:
            return 0
        try:
            self.site = None
            self.preloaded_pages = None
            intro_log = f"Running page cleanup for {wiki_name} wiki."
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
            namespace=0
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
                self.bot.bot.send_message(self.log_channel, f"Error during patrol: {e}")
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
        queued_pages = []
        ticker = Ticker()
        # # {{Featuredarticle}}
        # https://wot.fandom.com/wiki/Template:F/3
        # for fai in range(1, 38):
        #     page = pywikibot.Page(self.site, f"Template:F/{fai}")
        #     self.print_n(f"Processing {page.title()}...", end="", flush=True)
        #     page.get(get_redirect=False)
        #     page.text = "{{Featuredarticle}}<noinclude>[[Category:Do not feature]]</noinclude>"
        #     page.save(summary=f"{self.parsed_args.change_summary_prefix} (new featured article system)", bot=True, minor=False)
        for ns in self.site.namespaces:
            first_status_log = True
            self.print_n(f"Namespace {ns}", end="", flush=True)
            if ns != 0:
                self.print_n("")
                self.print_n(f"Skipping namespace {ns}")
                continue
            all_pages_gen = self.site.allpages(namespace=ns)
            self.preloaded_pages = pagegenerators.PreloadingGenerator(all_pages_gen, groupsize=50, quiet=True)
            # self.preloaded_pages = [ pywikibot.Page(self.site, p) for p in [ "Magla Daronos", "Perrin Aybara/Chronology", "Sorilea", "Strength in the One Power among Aes Sedai" ] ]
            with open(f"{self.parsed_args.changes_all_file}", "w") as all_changes_file:
                for page in self.preloaded_pages:
                    if ticker.tick():
                        if not first_status_log:
                            (self.parsed_args.verbosity == Verbosity.NORMAL) and print("")
                            self.print_n(f"{page_cnt:5d} pages read. {len(queued_pages):5d} queued. {pages_noperm:5d} skipped due to perms. {len(failed_pages):5d} pages produced errors.", end="", flush=True)
                        first_status_log = False
                    (self.parsed_args.verbosity == Verbosity.NORMAL) and print(".", end="", flush=True)
                    log.debug("Processing page: %s", page.title())
                    try:
                        page.get(get_redirect=True)
                        pre_text = page.text
                        mod = PageMod(page_id, urllib.parse.unquote(page.title()), [self.parsed_args.change_summary_prefix])
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
                        match = re.search(r"\/\/wot\.(fandom|wikia)", page.text, re.IGNORECASE | re.MULTILINE)
                        if (match):
                            log.warning(f"Page '{page.title()}' seems to contain a hard-coded wotwiki link even after cleanup: {match}:   \"{page.text[max(0, match.start()-20):min(len(page.text), match.end()+20)]}\"")
                            still_dirty.append(page.title())
                    except Exception as e:
                        err_log = f"Error processing page '{page.title()}':"
                        log.error(err_log, exc_info=True)
                        if self.bot and self.log_channel:
                            self.bot.bot.send_message(self.log_channel, f"{err_log} {e}")
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

exit(run_command(Patrol(sys.argv)))