import argparse
import json
import sys
import re
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
            default="./wiki/Module:Characters/characters.json",
            help="Path to the existing JSON file containing character data.")
        parser.add_argument(
            "--output-file",
            action="store",
            default="./characters.json",
            help="Path to the output JSON file containing character data.")
        return parser

    def run_command(self):
        if (Path(self.parsed_args.output_file).exists()):
            raise Exception(f"{self.parsed_args.output_file} already exists, refusing to overwrite.")
        log.info(f"Loading input file {self.parsed_args.input_file}")
        self.print_n("Processing characters", end="", flush=True)
        chars = None
        chars_orig = None
        with open(self.parsed_args.existing, "r", encoding='utf-8') as existing_file:
            chars = json.load(existing_file)
        with open(self.parsed_args.existing, "r", encoding='utf-8') as existing_file:
            chars_orig = json.load(existing_file)
        with open(self.parsed_args.input_file, "r", encoding='iso-8859-1') as input_f:
            column_names = input_f.readline().strip().split("\t")
            log.info(f"Column names: {column_names}")
            for line in input_f:
                if (line.startswith("#")):
                    continue
                if (self.parsed_args.verbosity == Verbosity.NORMAL):
                    print(".", end="", flush=True)
                fields = line.strip().split("\t")
                log.debug(f"fields: {fields}")
                name = None
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
                            if re.match(r".*\(.*", name):
                                raise Exception(f"Error: name {name} contains parentheses, which is not allowed")
                            if name not in chars:
                                chars[name] = {}
                            chars[name]["name"] = name
                        else:
                            key = col
                            set_val = True
                            if key == "strength":
                                set_val = False
                                strength_78 = None
                                strength_72 = None
                                strength_60 = None
                                match1 = re.match(r"^\+\+(\d+)", val)
                                match2 = re.match(r"^(\d+)\(\+(\d+)\)", val)
                                match3 = re.match(r"^(\d+)\((\d+)\)", val)
                                if match1:
                                    strength_72 = 1 - int(match1.group(1))
                                    strength_60 = strength_72 - 12
                                    strength_78 = strength_72 + 6
                                elif match2:
                                    strength_72 = int(match2.group(1))
                                    strength_60 = 1 - int(match2.group(2))
                                    strength_78 = strength_72 + 6
                                elif match3:
                                    strength_72 = int(match3.group(1))
                                    strength_60 = int(match3.group(2))
                                    strength_78 = strength_72 + 6
                                if strength_78 - 6 != strength_72 or strength_72 - 12 != strength_60:
                                    raise Exception(f"Error: strength value {val} does not match expected format (60: {strength_60}, 72: {strength_72}, 78: {strength_78})")
                                chars[name]["strength_78"] = strength_78
                            elif key == "faction":
                                set_val = False
                                old_key = None
                                new_val = None
                                if val == "White Tower":
                                    old_key = "wt_schism_faction"
                                    new_val = "Loyalist"
                                elif val == "Salidar Rebels":
                                    old_key = "wt_schism_faction"
                                    new_val = "Rebel"
                                elif val == "Sworn to Rand" or val == "Sworn to Rand al'Thor":
                                    old_key = "sworn_to_rand"
                                    new_val = True
                                elif val == "Liandrin's group":
                                    if "traits" not in chars[name]:
                                        chars[name]["traits"] = []
                                    add = True
                                    for t in chars[name]["traits"]:
                                        if t == "Liandrin's group":
                                            add = False
                                            break
                                    if add:
                                        chars[name]["traits"].append("Liandrin's group")
                                else:
                                    raise Exception(f"Error: unrecognized faction value {val} for character {name}")
                                if old_key != None:
                                    c = chars[name]
                                    if old_key in chars[name] and type(chars[name][old_key]) == dict:
                                        c = chars[name][old_key]
                                    if old_key in c and c[old_key] != new_val:
                                        raise Exception(f"Error: duplicate column name {col} (already have value {c[old_key]}, new value {new_val})")
                                    c[old_key] = new_val
                            elif key == "controller":
                                set_val = False
                                vals = val.split(",")
                                if len(vals) > 0:
                                    for i in range(len(vals)):
                                        vals[i] = vals[i].strip()
                                    chars[name]["shadow_controllers"] = vals
                            elif key == "notes":
                                set_val = False
                                if "notes" not in chars[name]:
                                    chars[name]["notes"] = []
                                if type(chars[name]["notes"]) == str:
                                    chars[name]["notes"] = [chars[name]["notes"]]
                                chars[name]["notes"].append(val)
                            if set_val:
                                log.debug(f"Setting {key} {col} {val} (current: {chars[name]})")
                                if key in chars[name] and chars[name][key] != val:
                                    raise Exception(f"Error: duplicate column name {col} (already have value {chars[name][key]}, new value {val})")
                                else:
                                    chars[name][key] = val
        if (self.parsed_args.verbosity == Verbosity.NORMAL):
            print("done", flush=True)
        self.print_v(f"Writing all characters to {self.parsed_args.output_file}")
        with open(self.parsed_args.output_file, "w") as f:
            json.dump(chars, f, indent=2, sort_keys=True)
        self.print_n(f"Wrote new characters to {self.parsed_args.output_file}.")
        self.compare("", chars_orig, chars)
        return 0

    def compare(self, lbl, orig, new):
        if type(orig) != type(new):
            if type(orig) == str and type(new) == list or type(new) == dict:
                self.print_n(f"{lbl}: Changed type from {type(orig)} to {type(new)}: {new}")
            else:
                raise Exception(f"{lbl}: Different types in new vs old: {type(orig)} vs {type(new)}")
        elif type(orig) == dict:
            for key in orig:
                if key not in new:
                    raise Exception(f"{lbl}: Removed {key} in new vs old")
                else:
                    self.compare(f"{lbl}.{key}", orig[key], new[key])
            for key in new:
                if key not in orig:
                    self.print_n(f"{lbl}: Added {key}")
        elif type(orig) == list:
            for i, val in enumerate(orig):
                if val not in new:
                    raise Exception(f"{lbl}: Removed value {val} in new vs old")
                else:
                    self.compare(f"{lbl}[{i}]", val, val)
            for val in new:
                if val not in orig:
                    self.print_n(f"{lbl}: Added value {val} in new vs old")
        elif new != orig:
            if orig == "" or orig == None:
                self.print_n(f"{lbl}: New value {new} (previously empty)")
            else:
                raise Exception(f"{lbl}: Different value in new vs old: {new} vs {orig}")

exit(run_command(ConvertTsvCharactersToJson(sys.argv)))