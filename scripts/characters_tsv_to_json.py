import argparse
import json
import math
import sys
import re
import time
from command import Command, Verbosity, run_command
from log_utils import logger as log
from pathlib import Path

class ConvertTsvCharactersToJson(Command):

    def __init__(self, args):
        Command.__init__(self, args)

    def create_arg_parser(self):
        parser = argparse.ArgumentParser(
            description=""
        )
        parser.add_argument(
            "--input-file",
            action="store",
            default="./characters.tsv",
            help="Path to the input TSV file containing character data.")
        parser.add_argument(
            "--existing",
            action="store",
            default="./pre_characters.json",
            help="Path to the existing JSON file containing character data.")
        parser.add_argument(
            "--output-file",
            action="store",
            default="./characters.json",
            help="Path to the output JSON file containing character data.")
        return parser

    def run_command(self):
        if (Path(self.parsed_args.output_file).exists()):
            raise Exception(f"{self.parsed_args.output_file} already exists, refusing to overwrite.");
        characters = {}
        log.info(f"Loading input file {self.parsed_args.input_file}")
        self.print_n("Processing characters", end="", flush=True)
        with open(self.parsed_args.input_file, "r") as input_f:
            column_names = input_f.readline().strip().split("\t")
            log.info(f"Column names: {column_names}")
            for line in input_f:
                if (self.parsed_args.verbosity == Verbosity.NORMAL):
                    print(".", end="", flush=True)
                fields = line.strip().split("\t")
                log.debug(f"fields: {fields}")
                name = None
                c = {}
                for col_i in range(len(column_names)):
                    if col_i >= len(fields):
                        continue
                    col = column_names[col_i]
                    val = fields[col_i]
                    if str.lower(val) == "true":
                        val = True
                    elif str.lower(val) == "false":
                        val = False
                    elif re.match(r"^\d+$", val):
                        val = int(val)
                    if not val == "":
                        if (col == "name"):
                            name = val
                        else:
                            keys = col.split(".")
                            c_lvl = c
                            for ki in range(len(keys)-1):
                                k = keys[ki]
                                log.debug(f"key: {k}")
                                if k not in c_lvl:
                                    c_lvl[k] = {}
                                c_lvl = c_lvl[k]
                            if keys[-1] in c_lvl:
                                raise Exception(f"Error: duplicate column name {col} (already have value {c_lvl[keys[-1]]}, new value {val})")
                            c_lvl[keys[-1]] = val
                            if(keys[-1] == "year") and not "calendar" in c_lvl:
                                c_lvl["calendar"] = c["calendar"]
                            # elif(col in { "calendar", "notes" }):
                            #     c[col] = val
                            # elif(col in { "origin", "ajah", "age_last", "status", "wt_schism_faction", "darkfriend", "years_novice", "years_accepted" }):
                            #     c[col] = {col: val}
                            # elif(col == "year_died" ):
                            #     if "died" not in c:
                            #         c["died"] = { "calendar": c["calendar"] }
                            #     c["died"]["year"] = val
                            # elif(col == "last_year" ):
                            #     if col not in c:
                            #         c[col] = { "calendar": c["calendar"] }
                            #     c[col]["year"] = val
                            # elif(col in { "strength_78" }):
                            #     if "channeler" not in c:
                            #         c["channeler"] = {}
                            #     c["channeler"][col] = {col: val}
                            # elif(col in { "years_as" }):
                            #     if "aes_sedai" not in c:
                            #         c["aes_sedai"] = {}
                            #     c["aes_sedai"]["years"] = {col: val}
                            # elif(col.endswith(".refs")):
                            #     base_col = col[:-5]
                            #     b = None
                            #     if base_col == "strength_78":
                            #         base_col = "channeler.strength_78"
                            #         if not "channeler" in c:
                            #             c["channeler"] = {}
                            #         if not "strength_78" in c["channeler"]:
                            #             c["channeler"]["strength_78"] = {}
                            #         b = c["channeler"]["strength_78"]
                            #     else:
                            #         if base_col not in c:
                            #             c[base_col] = {}
                            #         b = c[base_col]
                            #     b["refs"] = json.loads(val)
                            # else:
                            #     raise Exception(f"Error: unrecognized column name: {col}")
                characters[name] = c
        if (self.parsed_args.verbosity == Verbosity.NORMAL):
            print("done", flush=True)
        self.print_v(f"Loading existing JSON characters: {self.parsed_args.existing}")
        existing = json.load(open(self.parsed_args.existing, "r"))
        self.print_v(f"Merging existing characters with newly parsed characters")
        c = characters | existing
        self.print_v(f"Writing all characters to {self.parsed_args.output_file}")
        with open(self.parsed_args.output_file, "w") as f:
            json.dump(c, f, indent=2, sort_keys=True)
        self.print_n(f"Wrote {len(characters)} new characters to {self.parsed_args.output_file} (+{len(existing)} -> {len(c)}).")
        if (self.parsed_args.verbosity >= Verbosity.VERBOSE):
            with open(self.parsed_args.output_file, "r") as f:
                for line in f:
                    self.print_v(line, end="", flush=True)
        return 0

exit(run_command(ConvertTsvCharactersToJson(sys.argv)))