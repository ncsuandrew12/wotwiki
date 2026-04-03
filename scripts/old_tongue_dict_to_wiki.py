import argparse
import json
import math
import os
import sys
import re
import time
from command import Command, Progresser, Verbosity, run_command
from log_utils import logger as log
from pathlib import Path
from utils import Ticker

class ConvertOtDictToWiki(Command):

    def __init__(self, args):
        Command.__init__(self, args)

    def create_arg_parser(self):
        parser = argparse.ArgumentParser(
            description=""
        )
        parser.add_argument(
            "--input-file",
            action="store",
            default="source material/companion-old-tongue.md",
            help="Path to the input Markdown file containing the Old Tongue dictionary.")
        parser.add_argument(
            "--out-json",
            action="store",
            default="source material/companion-old-tongue.json",
            help="Path to the output JSON file.")
        parser.add_argument(
            "--out-json-force",
            action="store_true",
            help="Overwrite the output JSON file.")
        return parser

    def finish_entry(self, entries, entry):
        log.debug(f"Finishing entry: {entry}")
        new_entries = []
        r = r"(.*)\[([^\]]+)-*\]-*(\([^\)]+\)){0,1}\s*(\S.*)"
        match = re.match(r, entry["definition"])
        while match:
            log.debug("Contains another entry")
            entry["definition"] = re.sub(r"\s*;*\s*$", "", re.sub(r, r"\1", entry["definition"], count=1))
            ne = { "word": match.group(2), "definition": match.group(4) }
            if len(match.group(3) or "") > 2:
                ne["part"] = match.group(3)[1:-1]
            elif "part" in entry:
                ne["part"] = entry["part"]
            elif "ref" in entry:
                ne["ref"] = entry["ref"]
            entries[entry['word']] = entry
            new_entries.append(ne)
            match = re.match(r, entry["definition"])
        for entry in new_entries:
            entries[entry['word']] = entry
            self.finish_entry(entries, entry)

    def run_command(self):
        if (not self.parsed_args.out_json_force and Path(self.parsed_args.out_json).exists()):
            raise Exception(f"{self.parsed_args.out_json} already exists, refusing to overwrite.")
        log.info(f"Loading input file {self.parsed_args.input_file}")
        self.print_n("Processing words", end="", flush=True)
        entries = {}
        entry = None
        progresser = Progresser(self)
        with open(self.parsed_args.input_file, "r") as input_f:
            for line in input_f:
                line = line.strip()
                log.debug(f"line: {line}")
                progresser.tick()
                if line == "":
                    self.finish_entry(entries, entry)
                    entry = None
                else:
                    if entry == None:
                        match = re.match(r'^\[{0,1}([^\]]+)-*\]{0,1}-*(\([^\)]+\)){0,1}\s*(\S.*)$', line)
                        if not match:
                            raise Exception(f"Error: unrecognized entry format: {line}")
                        entry = { "word": match.group(1), "definition": match.group(3) }
                        if len(match.group(2) or "") > 2:
                            entry["part"] = match.group(2)[1:-1]
                        entry["ref"] = { "book": "twotc", "entry": "otdict", "word": entry["word"] }
                        entries[entry["word"]] = entry
                    else:
                        entry["definition"] += " " + line
        if entry:
            self.finish_entry(entries, entry)
        progresser.done()
        self.print_v(f"Parsed {len(entries)} entries. Writing to {self.parsed_args.out_json}...", end="", flush=True)
        with open(self.parsed_args.out_json, "w") as f:
            json.dump(entries, f, indent=2, sort_keys=True)
        self.print_v("done", flush=True)
        self.print_n(f"Wrote {len(entries)} entries to {self.parsed_args.out_json}.")
        return 0

exit(run_command(ConvertOtDictToWiki(sys.argv)))