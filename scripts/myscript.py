# source /home/andrewf/w/wotwiki/pywikibot/bin/activate
# %pip install pywikibot
# %pip install Requests

import json
import logging
import os
import shutil
import string
import sys
import time
import pywikibot
import random
import re
import subprocess
import urllib.parse
from pathlib import Path
from logging.handlers import RotatingFileHandler
from pywikibot import pagegenerators

class MaxLogLevelFilter(logging.Filter):
    def __init__(self, logLevel):
        self.logLevel = logLevel

    def filter(self, record):
        return record.levelno <= self.logLevel

    logLevel = logging.DEBUG

class Formatter(logging.Formatter):
    def format(self, record):
        record.timeZone = "EST"
        record.levelnameSuffix = (" " * (len("CRITICAL") - len(record.levelname)))
        return logging.Formatter.format(self, record)

formatter = Formatter(
    fmt="%(asctime)s %(timeZone)s %(processName)s:%(threadName)s %(levelname)s:%(levelnameSuffix)s %(pathname)s:%(lineno)d(%(funcName)s) %(message)s",
    datefmt=None)
logDir = os.path.dirname(os.path.realpath(__file__))
fileHandler = RotatingFileHandler(
    filename=os.path.join(logDir, "log.log"),
    maxBytes=5 * 1024 * 1024, # 5MB
    backupCount=9,
    delay=True)
fileHandler.setFormatter(formatter)

log = logging.getLogger("myscript")

stdoutHandler = logging.StreamHandler(stream=sys.stdout)
stdoutHandler.setFormatter(formatter)

stderrHandler = logging.StreamHandler(stream=sys.stderr)
stderrHandler.setFormatter(formatter)

log.addHandler(fileHandler)
log.addHandler(stderrHandler)

logging.getLogger().setLevel(logging.NOTSET)
stdoutHandler.setLevel(logging.INFO)
stdoutHandler.addFilter(MaxLogLevelFilter(logging.WARNING))
stderrHandler.setLevel(logging.ERROR)

wiki_name = "wot"
language = "en"
# screenName = "Androlf" # Username used on Fandom, i.e. a user "Roger" may make a Fandom account called "Roger Bot", use "Roger Bot". 
# botName = "androlf-bot" # Bot name that you choose via Special:BotPasswords, i.e. "Roger_community_bot"

hard_ww_link_re = r"\[http(s){0,1}://(www\.){0,1}wot\.(fandom|wikia).com\/wiki\/([^ ]+) ([^\]]+)\]"
mod_queue_dir_path = "mod_queue"
mod_queue_json_path = mod_queue_dir_path + "/queue.json"

DRY_RUN = False

def CreateTmpFile(baseFilename=None, mutate=False, maxRetries=2):
    if baseFilename == None:
        baseFilename = "/tmp/" + "".join(random.choice(string.ascii_lowercase) for i in range(15))
        mutate = True
    filenameSuffix = ""
    ex = None
    attemptNum = 1
    while maxRetries < 0 or attemptNum <= 1 + maxRetries:
        filename = baseFilename + filenameSuffix
        try:
            return open(filename, 'x')
        except Exception as e:
            log.debug("Exception while creating tmp file (attempt %d): %s", attemptNum, filename)
            ex = e
        attemptNum+=1
        if mutate:
            filenameSuffix = ".{}".format(attemptNum)
    raise ex

def RunSubprocess(
    cmdArgs,
    shell=False,
    timeout=0,
    throwOnStdErr=True,
    expectedReturnCode=0,
    throwOnUnexpectedReturnCode=True,
    logAndReturnStdout=True,
    stdoutFilePath=None,
    stderrFilePath=None
):
    fullCmd = " ".join(cmdArgs)
    stdoutFile = None
    stderrFile = None
    try:
        if stdoutFilePath is not None:
            stdoutFile = open(stdoutFilePath, 'w')
        else:
            stdoutFile = CreateTmpFile()
        if stderrFilePath is not None:
            stderrFile = open(stderrFilePath, 'w')
        else:
            stderrFile = CreateTmpFile()
        log.debug(
            "command (stdoutFile=%s, stderrFile=%s, shell=%s): %s",
            stdoutFile.name,
            stderrFile.name,
            shell,
            fullCmd)
        # Do NOT use subprocess.run(). Some commands seem to hang, probably because of issues with directing
        # stdout/stderr to in-memory "pipes". subprocess.run() does not have the option to specify output files for
        # stdout and stderr.
        subp = subprocess.Popen(fullCmd if shell else cmdArgs, shell=shell, stdout=stdoutFile, stderr=stderrFile)
        subp.stdoutFilePath = stdoutFile.name
        subp.stderrFilePath = stderrFile.name
        if timeout==0:
            success=False
            while not success:
                try:
                    subp.communicate(timeout=60)
                    success=True
                except subprocess.TimeoutExpired as e:
                    log.debug(e)
        else:
            try:
                subp.communicate(timeout=timeout)
            except subprocess.TimeoutExpired:
                subp.kill()
                subp.communicate()
                raise
        subp.stdout = None
        if logAndReturnStdout:
            with open(stdoutFile.name, 'r') as stdoutFile2:
                for line in stdoutFile2:
                    if subp.stdout == None:
                        log.debug("stdout (%s):", stdoutFile2.name)
                        subp.stdout = ""
                    log.debug("%s", line.rstrip('\n'))
                    # TODO Do something better/more efficient in case the file is very large
                    subp.stdout = subp.stdout + line
        subp.stderr = None
        with open(stderrFile.name, 'r') as stderrFile2:
            for line in stderrFile2:
                if subp.stderr == None:
                    log.debug("stderr (%s):", stderrFile2.name)
                    subp.stderr = ""
                log.debug("%s", line.rstrip('\n'))
                # TODO Do something better/more efficient in case the file is very large
                subp.stderr = subp.stderr + line
        if subp.stderr and len(subp.stderr) > 0:
            if throwOnStdErr:
                raise Exception("stderr output during command: {}: {}".format(fullCmd, subp.stderr[0:256]))
        # TODO After logging stdout/stderr, delete the files (only in success case?)
        if throwOnUnexpectedReturnCode and not subp.returncode == expectedReturnCode:
            raise Exception("Unexpected return code ({}, expected {}): {}".format(
                subp.returncode,
                expectedReturnCode,
                fullCmd))
        return subp
    finally:
        if stdoutFile is not None:
            stdoutFile.close()
        if stderrFile is not None:
            stderrFile.close()

class PageMod():
    def __init__(self, id, title):
        self.id = id
        self.title = title
    
    def to_dict(self):
        """Convert PageMod object to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'title': self.title
        }
    
    @classmethod
    def from_dict(cls, data):
        """Create PageMod object from dictionary (for JSON deserialization)."""
        return cls(data['id'], data['title'])
    
    def to_json(self):
        """Convert PageMod object to JSON string."""
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_json(cls, json_str):
        """Create PageMod object from JSON string."""
        data = json.loads(json_str)
        return cls.from_dict(data)

def create_queue():
    mod_queue = []
    still_dirty = []
    page_num = 0
    page_cnt = 0
    page_id = 1
    pages_modified = 0
    pages_noperm = 0
    with open(f"changes-all.diff", "w") as all_changes_file, open(f"changes.diff", "w") as changes_file:
        for page in preloaded_pages:
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
                mod = PageMod(page_id, page.title())
                mod_path = f"{mod_queue_dir_path}/{mod.id}"
                os.makedirs(mod_queue_dir_path, exist_ok=True)
                os.makedirs(mod_path, exist_ok=False)
                pre_path = f"{mod_path}-pre.wiki"
                post_path = f"{mod_path}-post.wiki"
                with open(pre_path, "w") as f:
                    f.write(pre_text)
                with open(post_path, "w") as f:
                    f.write(page.text)
                subp = RunSubprocess(
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
            page_num = (page_num % page_group_size) + 1
            page_cnt = page_cnt + 1
    if len(mod_queue) > 0:
        with open(mod_queue_json_path, "w") as f:
            json.dump([mod.to_dict() for mod in mod_queue], f, indent=2, sort_keys=True)
    log.info(f"Pages that will still contain hard-coded wotwiki links after changes are applied: {still_dirty}")
    log.info(f"{page_cnt} pages read. {pages_modified} queued. {pages_noperm} skipped due to perms.")

def process_queue():
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
        log.info(f"Processing {mod.title} (id={mod.id})")
        page = pywikibot.Page(site, mod.title)
        page.get(force=True, get_redirect=True)
        pre_path = f"{mod_queue_dir_path}/{mod.id}-pre.wiki"
        post_path = f"{mod_queue_dir_path}/{mod.id}-post.wiki"
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
                if (not DRY_RUN):
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

# user_file = "user-config.py"
# password_file = f"{screenName}@{botName}_password.py".format(screenName=screenName, botName=botName)

# # Create the user-config.py file required by pywikibot, we'll create a separate file for this so pywikibot can find it.
# config_text = f"""
# usernames['{wiki_name}']['{language}'] = '{screenName}@{botName}' # Note this is a combination of two names. The Special:BotPasswords page will tell you what to put here.

# # Put password into config manually - this is better practice
# password_file = '{password_file}'
# """

# Populate the PASSWORD information here, NOTE: older accounts may need to use a combination of {botName}@<Password> here.
# As mentioned above, it's better to split the password out, but for the purpose of this guide, this is included in a python cell.
# credentials = "('{screenName}', BotPassword('{botName}', '<Password>'))" # For new passwords/accounts, expect this to just be the text after the "@".
# with open("password.py", "w") as f:
#     f.write(credentials.format(botName=botName, screenName=screenName, language=language, wiki_name=wiki_name))
# print("password.py created!")

# cfg_path = Path(user_file)
# if not cfg_path.exists():
#     with open(cfg_path, "w") as f:
#         f.write(config_text.format(wiki_name=wiki_name, language=language, botName=botName, screenName=screenName, password_file=password_file))
#     print("user config created!")

# # Generate the contents of the family file, this uses the wiki_name variable set above
# family_file = """
# from pywikibot import family

# class Family(family.Family):
#     name = '{wiki_name}'
#     langs = {{
#         'en': '{wiki_name}.fandom.com'
#     }}

#     def scriptpath(self, code):
#         return '/'

#     def apipath(self, code):
#         return '/api.php'
# """

# # Name the file after the Fandom wiki you want to go for, if I want the domo.fandom.com wiki, I would have "<name>" as "domo"
# family_file_name = f"families/{wiki_name}_family.py".format(wiki_name=wiki_name)
# # Create local directory to help the wikibot find the family. The wiki bot expects the family files in a "families" directory.
# if not Path(family_file_name).exists():
#     os.makedirs(os.path.dirname(family_file_name), exist_ok=True) # Create the directory if it didn't already exist.
#     with open(family_file_name, "w") as f:
#         f.write(family_file.format(wiki_name=wiki_name))
#     print("Fandom family file created!")

# Set the pywikibot directory to be one level up on the active file path which gives it visibility of the local user-config, password file and families.
os.environ["PYWIKIBOT_DIR"] = os.path.abspath("../")
# print("env: " + os.environ["PYWIKIBOT_DIR"])

# wiki_name comes from variables above, i.e. domo.fandom.com this wiki_name variable would be "domo"
site = pywikibot.Site("en", "wot")
site.login()
print("Logged in successfully!")

all_pages_gen = site.allpages(namespace=0)
page_group_size = 50
preloaded_pages = pagegenerators.PreloadingGenerator(all_pages_gen, groupsize=page_group_size)
# preloaded_pages = [ pywikibot.Page(site, p) for p in [ "Author unknown", "Mallard's Hill" ] ]

# This is deliberately not an if/else
if not Path(mod_queue_dir_path).is_dir():
    create_queue()
if Path(mod_queue_dir_path).is_dir():
    process_queue()
