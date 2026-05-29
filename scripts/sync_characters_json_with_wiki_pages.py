# This script requires pywikibot to be properly configured with a families/wot_family.py and a user file.
# Example user file for a bot named "androlf-bot" for a user named "androlf":
# Filename: Androlf@androlf-bot_password.py
# Contents:
#('Androlf', BotPassword('androlf-bot', 'putThePasswordHere'))

import argparse
import json
import logging
import os
import pathlib
from pathlib import Path
import pywikibot
from pywikibot import sleep
from pywikibot.exceptions import NoPageError
import re
import shutil
import sys
import wikitextparser as wtp

import utils
from command import Command, Verbosity, run_command
from discord_logger import DWP, DWT
from log_utils import logger as log
from page_mod import PageMod
from ticker import Ticker

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
        # TODO Move common wiki-editing args (save-changes, etc) to a common location instead of duplicating in all scripts.
        parser.add_argument(
            "--character-json",
            action="store",
            default="./wiki/Module:Characters/characters.json",
            help="Path to the characters JSON file.")
        parser.add_argument(
            "--character-json-remaining",
            action="store",
            default="./wiki/Module:Characters/characters-remaining.json",
            help="Path to the remaining characters JSON file.")
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
            default="(bot) json-to-wiki sync.",
            help="Prefix to use for change summaries when saving changes.")
        parser.add_argument(
            "--discard-queue",
            action="store_true",
            default=False,
            help="If set, the script will discard the modification queue before processing.")
        return parser
    
    def run_command(self):
        # q = json.load(open("/home/andrewf/w/wotwiki/scratch/wiki/Module:Quotes/quotes.json", "r"))
        # q["tags"] = dict(sorted(q["tags"].items()))
        # with open("/home/andrewf/w/wotwiki/scratch/wiki/Module:Quotes/quotes_sorted.json", "w") as f:
        #     json.dump(q, f, indent=4)
        try:
            self.site = None
            self.preloaded_pages = None
            intro_log = f"Running character sync for {wiki_name} wiki."
            log.info(intro_log)
            self.process_args()
            log.log(self.parsed_args.save_changes and logging.INFO or logging.WARNING,
                "self.parsed_args.save_changes is %s, this run %s save changes to the wiki!",
                self.parsed_args.save_changes,
                self.parsed_args.save_changes and "MAY" or "WILL NOT")
            # Set the pywikibot directory to be one level up on the active file path which gives it visibility of the local user-config, password file and families.
            os.environ["PYWIKIBOT_DIR"] = os.path.abspath("../")
            # print("env: " + os.environ["PYWIKIBOT_DIR"])
            # wiki_name comes from variables above, i.e. domo.fandom.com this wiki_name variable would be "domo"
            self.site = pywikibot.Site("en", wiki_name)
            self.site.login()
            self.print_n(f"Logged into wiki {wiki_name} successfully!")
            if Path(mod_queue_dir_path).is_dir() and self.parsed_args.discard_queue:
                self.print_n(f"Discarding modification queue at {mod_queue_dir_path}")
                shutil.rmtree(mod_queue_dir_path)
            if not Path(mod_queue_dir_path).is_dir():
                self.create_queue()
            if Path(mod_queue_dir_path).is_dir():
                self.process_queue()
        except Exception as e:
            log.error("Error during character sync: %s", e, exc_info=True)
            # log.error(e)
            raise
        return 0

    def process_args(self):
        log.debug("Processing arguments.")
        self.parsed_args.change_summary_prefix = self.parsed_args.change_summary_prefix.strip()

    def sanitize_str_for_filename(self, s):
        # s = re.sub(r"\s+", "_", s)
        s = re.sub(r"\u2019", "", s)
        s = re.sub(r"[^a-zA-Z0-9_\-\\\/ \'\:]", "", s)
        # s = re.sub(r"_+", "_", s)
        return s

    def get_val_or_epon_dict_value(self, obj, key):
        if key not in obj:
            return None
        elif type(obj[key]) == dict:
            if key in obj[key]:
                return obj[key][key]
            raise Exception("Missing nested key %r: %r for object %r", (key, obj[key], obj))
        return obj[key]

    def get_field_refs(self, obj, key):
        if key not in obj or type(obj[key]) != dict:
            return None
        if "refs" in obj[key]:
            return obj[key]["refs"]
        return None
    
    def override_template_param(self, page, mod, template, param_idx, param_name, jsonval, jsonval_norm):
        val = template.arguments[param_idx].value.strip()
        if str(val) != str(jsonval_norm):
            if val and len(val) > 0:
                log.warning("%r mismatch on page %s: JSON %r is %r -> %r but wiki page has %r.", param_name, page, param_name, jsonval, jsonval_norm, val)
            if jsonval_norm is not None:
                log.info("Overriding %r for page %s: %r -> %r", template.arguments[param_idx].name, page, val, jsonval_norm)
                mod.summary.append(f"[{template.arguments[param_idx].name}]")
                template.set_arg(template.arguments[param_idx].name, f"{jsonval_norm}\n")
            return True
        return False

    def create_queue(self):
        mod_queue = []
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
                char_dwp = DWP(char)
                if ticker.tick():
                    if not first_status_log:
                        (self.parsed_args.verbosity == Verbosity.NORMAL) and print("")
                        self.print_n(f"{page_cnt:5d}/{len(chars)} characters processed. {len(queued_pages):5d} queued. {pages_noperm:5d} skipped due to perms. {len(failed_pages):5d} pages produced errors.", end="", flush=True)
                    first_status_log = False
                name = self.get_val_or_epon_dict_value(chars[char], "name") or char
                if name is None:
                    raise Exception("Name is None for character '{}' in JSON.".format(char_dwp))
                page = self.get_val_or_epon_dict_value(chars[char], "page") or char or name
                if page is None:
                    failed_pages.append(char_dwp)
                    raise Exception("Character '{}' does not have a name or page field in the JSON.".format(char_dwp))
                self.print_v(f"Character {name}", end="", flush=True)
                page = pywikibot.Page(self.site, page)
                (self.parsed_args.verbosity == Verbosity.NORMAL) and print(".", end="", flush=True)
                log.debug("Processing page: %s", page)
                try:
                    try:
                        attempts = 3
                        while attempts > 0:
                            try:
                                page.get(force=True, get_redirect=True)
                                attempts = 0
                            except KeyboardInterrupt as e:
                                log.warning("KeyboardInterrupt received.", exc_info=True)
                                sleep(3)
                            attempts -= 1
                    except NoPageError as e:
                        missing_pages.append(page.title())
                        raise
                    changed = False
                    pre_text = page.text
                    mod = PageMod(page_id, page=page, summary=[self.parsed_args.change_summary_prefix])
                    parsed = wtp.parse(page.text)
                    char_templ_idx = None
                    for idx, template in enumerate(parsed.templates):
                        template_dwt = DWT(template)
                        log.debug("Processing %s on page %s", template_dwt, page)
                        if template.name.strip().lower() == "character":
                            if char_templ_idx is not None:
                                raise Exception(f"Multiple character templates found on page '{page.title()}': {parsed.templates}")
                            char_templ_idx = idx
                    # TODO: Add character template if it's missing.
                    if char_templ_idx == None:
                        raise Exception(f"Character template not found on page '{page.title()}'.")
                    black_ajah = None
                    ajahs = self.get_val_or_epon_dict_value(chars[char], "ajahs")
                    ajah = self.get_val_or_epon_dict_value(chars[char], "ajah")
                    if ajahs is None and ajah is not None:
                        ajahs = []
                    if ajah is not None:
                        ajahs.append(ajah)
                    has_ajah = False
                    for idx, ajah in enumerate(ajahs or []):
                        if ajah == "NA":
                            ajahs[idx] = "No"
                        elif ajah is not None and len(ajah) > 0:
                            has_ajah = True
                    darkfriend = self.get_val_or_epon_dict_value(chars[char], "darkfriend")
                    copy_fields = [
                        "male",
                        "female",
                        "darkfriend",
                        "age_enrolled_novice",
                        "novice_years",
                        "accepted_years",
                        "aes_sedai_years",
                        "wt_schism_faction"
                    ]
                    if darkfriend == True and has_ajah:
                        black_ajah = True
                    targ_idxs = {}
                    for idx, param in enumerate(parsed.templates[char_templ_idx].arguments):
                        param_name = param.name.strip().lower()
                        if param_name in targ_idxs:
                            raise Exception(f"Duplicate parameter '{param.name}' -> '{param_name}' in {template_dwt} on page {page.title()}")
                        log.debug("Processing parameter %r -> %r in %s on page %s", param.name, param_name, template_dwt, page)
                        targ_idxs[param_name] = idx
                    # self.print_n(f"page '{page}': changed: {changed}")
                    if black_ajah == True and name != "Verin Mathwin":
                        if "affiliation" in targ_idxs:
                            changed = self.override_template_param(page, mod, parsed.templates[char_templ_idx], targ_idxs["affiliation"], "affiliation", None, "Black Ajah") or changed
                        else:
                            log.info("Adding affiliation for character %s on page %s: 'Black Ajah'.", char_dwp, page)
                            mod.summary.append("[ajah (black)]")
                            parsed.templates[char_templ_idx].set_arg("affiliation", "Black Ajah\n")
                            changed = True
                    # self.print_n(f"page '{page}': changed: {changed}")
                    for idx, ajah in enumerate(ajahs or []):
                        key = "ajah"
                        if idx > 0:
                            key = f"ajah{idx+1}"
                        if key in targ_idxs:
                            changed = self.override_template_param(page, mod, parsed.templates[char_templ_idx], targ_idxs[key], key, ajah, ajah) or changed
                        else:
                            if ajah is not None and len(ajah) > 0:
                                log.info("Adding %r for character %s on page %s: %s.", key, char_dwp, page, ajah)
                                mod.summary.append(f"[{key}]")
                                parsed.templates[char_templ_idx].set_arg(key, f"{ajah}\n")
                                changed = True
                    if "name" in targ_idxs:
                        name = re.sub(r"\s*\(.*$", "", name)
                        changed = self.override_template_param(page, mod, parsed.templates[char_templ_idx], targ_idxs["name"], "name", name, name) or changed
                    else:
                        pass
                        # if name is not None and len(name) > 0:
                        #     log.info(f"Adding name for character '{char_dwp}' on page '{page.title()}': '{name}'.")
                        #     mod.summary.append(f"[name]")
                        #     parsed.templates[char_templ_idx].set_arg("name", f"{name}\n")
                        #     changed = True
                    for cf in copy_fields:
                        log.info("Checking %r for character %s on page %s.", cf, char_dwp, page)
                        val = self.get_val_or_epon_dict_value(chars[char], cf)
                        if val is not None:
                            if cf in targ_idxs:
                                changed = self.override_template_param(page, mod, parsed.templates[char_templ_idx], targ_idxs[cf], cf, val, val) or changed
                            else:
                                log.info("Adding %r for character %s on page %s: %r.", cf, char_dwp, page, val)
                                mod.summary.append(f"[{cf}]")
                                parsed.templates[char_templ_idx].set_arg(f"{cf}", f"{val}\n")
                                changed = True
                            refs = self.get_field_refs(chars[char], cf)
                            ref_wt = None
                            if refs is not None:
                                for r in refs:
                                    if ref_wt == None:
                                        ref_wt = ""
                                    ref_wt += f"{{{{ref|{r['book']}|{r['chapter']}}}}}"
                            rkey = f"{cf}_refs"
                            if rkey in targ_idxs:
                                changed = self.override_template_param(page, mod, parsed.templates[char_templ_idx], targ_idxs[rkey], rkey, ref_wt, ref_wt) or changed
                            else:
                                if ref_wt is not None:
                                    log.info("Adding references for character %s on page %s: %r: %r.", char_dwp, page, rkey, ref_wt)
                                    mod.summary.append(f"[{rkey}]")
                                    parsed.templates[char_templ_idx].set_arg(f"{rkey}", f"{ref_wt}\n")
                                    changed = True
                            del chars[char][cf]
                    if (changed == True):
                        # self.print_n(f"Setting text for page '{page.title()}'")
                        page.text = str(parsed)
                    if pre_text != page.text:
                        mod_path = f"{mod_queue_dir_path}/{self.sanitize_str_for_filename(mod.get_title())}"
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
                            mod_queue.append(mod)
                            queued_pages.append(mod.get_title())
                            page_id += 1
                            with open(f"{mod_path}/changes.patch", "w") as changes_file:
                                changes_file.write(subp.stdout)
                                changes_file.write("\n")
                        else:
                            page.text = pre_text
                            log.warning("Page %s needs update but bot is not allowed to edit it. Summary: %s", page, mod.summary)
                            pages_noperm += 1
                    for key in ["ajah", "ajahs"]:
                        if key in chars[char]:
                            del chars[char][key]
                except Exception as e:
                    exc_info = True
                    err_log = f"Error processing page '{page.title()}':"
                    if isinstance(e, NoPageError):
                        err_log = f"Page '{page.title()}' does not exist."
                        exc_info = False
                        log.debug(err_log, exc_info=exc_info)
                    else:
                        log.error(err_log, exc_info=exc_info)
                    failed_pages.append(page.title())
                page_cnt = page_cnt + 1
        if len(mod_queue) > 0:
            os.makedirs(mod_queue_dir_path, exist_ok=True)
            with open(mod_queue_json_path, "w") as f:
                json.dump([mod.to_dict() for mod in mod_queue], f, indent=2, sort_keys=True)
        with open(self.parsed_args.character_json_remaining, "w") as f:
            json.dump(chars, f, indent=2, sort_keys=True)
        log.debug("Failed pages: %s", failed_pages)
        if failed_pages and len(failed_pages) > 0:
            log.warning("Failed pages: %s", failed_pages)
        log.debug("Missing pages: %s", missing_pages)
        log.info("Queued pages: %s", queued_pages)
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
            mod_dwp = DWP(mod.get_title())
            log.info("Processing %s", mod_dwp)
            page = mod.page or pywikibot.Page(self.site, mod.get_title())
            page.get(force=True, get_redirect=True)
            pre_path = f"{mod_queue_dir_path}/{mod.get_title()}/pre.wiki"
            post_path = f"{mod_queue_dir_path}/{mod.get_title()}/post.wiki"
            pre_text = None
            post_text = None
            try:
                with open(pre_path, "r") as f:
                    pre_text = f.read()
                if page.text != pre_text:
                    log.warning("Page text has changed since queue creation for %s, skipping modification.", mod_dwp)
                    shifted_pages.append(mod.get_title())
                    os.remove(pre_path)
                    os.remove(post_path)
                    continue
                with open(post_path, "r") as f:
                    post_text = f.read()
                page.text = post_text
                try:
                    log.info("Saving %s with summary: %s", mod_dwp, mod.summary)
                    if (self.parsed_args.save_changes):
                        page.save(summary=mod.summary, bot=True, minor=True)
                        post_page = mod.page or pywikibot.Page(self.site, mod.get_title())
                        if post_page.text != post_text:
                            raise Exception(f"Post-save text does not match expected text for '{mod_dwp}' following supposedly successful save.")
                        os.remove(pre_path)
                        os.remove(post_path)
                        pages_saved += 1
                except Exception as e:
                    err_log = f"Error saving page '{mod_dwp}'"
                    log.error(err_log, exc_info=True)
                    failed_pages.append(mod.get_title())
            except Exception as e:
                err_log = f"Error processing page '{mod_dwp}'"
                log.error(err_log, exc_info=True)
                failed_pages.append(mod.get_title())
        if len(shifted_pages) > 0:
            log.warning("The following pages were skipped due to text changes since queue creation: %s", shifted_pages)
            json.dump(shifted_pages, open(f"{mod_queue_dir_path}/shifted_pages.json", "w"), indent=2, sort_keys=True)
        if len(failed_pages) > 0:
            log.warning("The following pages failed to update: %s", failed_pages)
        if len(shifted_pages) + len(failed_pages) == 0:
            shutil.rmtree(mod_queue_dir_path)
        self.print_n(f"{pages_saved} pages saved. {len(shifted_pages)} pages skipped. {len(failed_pages)} pages failed.")

exit(run_command(SyncCharactersJsonWithWikiPages(sys.argv)))