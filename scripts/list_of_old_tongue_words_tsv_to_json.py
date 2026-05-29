import argparse
import json
import math
import os
import sys
import re
import time
from command import Command, run_command
from log_utils import logger as log
from pathlib import Path
from ticker import Ticker

class ConvertOtDictToWiki(Command):

    def __init__(self, args):
        Command.__init__(self, args)

    def create_arg_parser(self):
        parser = argparse.ArgumentParser(
            description=""
        )
        parser.add_argument(
            "--single-input-file",
            action="store",
            default="./OTSingle.txt")
        parser.add_argument(
            "--compound-input-file",
            action="store",
            default="./OTCompound.txt")
        parser.add_argument(
            "--in-json",
            action="store",
            default="../wotwiki/source-material/companion-old-tongue.json",
            help="Path to the input JSON file.")
        parser.add_argument(
            "--out-json",
            action="store",
            default="./old-tongue-dict.json")
        return parser

    def run_command(self):
        otd = json.load(open(self.parsed_args.in_json, "r"))
        with open(self.parsed_args.single_input_file, "r", encoding="cp1252") as f:
            for line in f:
                line = line.strip()
                log.debug(f"Processing line: {line}")
                if line == "" or line.startswith("#"):
                    continue
                word, defn, part = line.split("\t")
                parts = self.get_parts(part, line)
                if not word in otd:
                    otd[word] = { "word": word, "definition": { "wotwiki_custom": defn }, "parts": parts }
                elif "entries" not in otd[word]:
                    otd[word] = { "word": word, "entries": [ otd[word], { "definition": { "wotwiki_custom": defn }, "parts": parts } ] }
                    self.fixup_entry(otd[word])
                else:
                    otd[word]["entries"].append({ "definition": { "wotwiki_custom": defn }, "parts": parts })
        with open(self.parsed_args.compound_input_file, "r", encoding="cp1252") as f:
            for line_str in f:
                line_str = line_str.strip()
                log.debug(f"Processing line: {line_str}")
                if line_str == "" or line_str.startswith("#"):
                    continue
                try:
                    word, common, literal, part, notes, _ = line_str.split("\t")
                except Exception as e:
                    raise Exception(f"Error processing line_str: {line_str}: {e}")
                parts = self.get_parts(part, line)
                parts.append({ "type": "compound" })
                if not word in otd:
                    otd[word] = { "word": word, "definition": { "wotwiki_common": common, "wotwiki_literal": literal }, "parts": parts, "notes": notes }
                elif "entries" not in otd[word]:
                    otd[word] = { "word": word, "entries": [ otd[word], { "definition": { "wotwiki_common": common, "wotwiki_literal": literal }, "parts": parts, "notes": notes } ] }
                    self.fixup_entry(otd[word])
                else:
                    otd[word]["entries"].append({ "definition": { "wotwiki_common": common, "wotwiki_literal": literal }, "parts": parts, "notes": notes })
        with open(self.parsed_args.out_json, "w") as f:
            json.dump(otd, f, indent=2)
        return 0

    def get_parts(self, part, line):
        parts = []
        for _, part in enumerate(re.sub(r";\s+", ";", part).split(";")):
            modifiers = []
            match = re.match(r"^(.+)\s+\(([^)]+)\)$", part)
            if match:
                part = match.group(1).strip()
                m = match.group(2).strip()
                if m not in [ "auxiliary", "for nouns", "for adjectives", "possessive" ]:
                    raise Exception(f"Error: unrecognized part of speech modifier: {m}: {line}")
                modifiers.append(m)
            if part not in [ "adjective", "interjection", "adverb","combination","conjunction","noun",
                            "past participle","possessive pronoun","prefix","preposition","pronoun",
                            "relative pronoun","verb","suffix", "past participle" ]:
                if part == "nou":
                    part = "noun"
                elif part == "past partciple":
                    part = "past participle"
                else:
                    raise Exception(f"Error: unrecognized part of speech: {part}: {line}")
            p = { "type": part }
            if len(modifiers) > 0:
                p["modifiers"] = modifiers
            parts.append(p)
        return parts

    def fixup_entry(self, entry):
        del entry["entries"][0]["word"]
        if "italicize" in entry["entries"][0]:
            entry["italicize"] = entry["entries"][0]["italicize"]
            del entry["entries"][0]["italicize"]

exit(run_command(ConvertOtDictToWiki(sys.argv)))