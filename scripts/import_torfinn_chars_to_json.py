import argparse
import copy
import csv
import json
import sys
import re
import wot_books
from command import Command, Verbosity, run_command
from log_utils import logger as log
from pathlib import Path
from wot_books import books

wot_books.setup()

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
            default="../wotwiki/data/u-JaimTorfinn/WoT_CharacterNames_Data_v1.csv",
            help="Path to the input CSV file containing character data.")
        parser.add_argument(
            "--existing",
            action="store",
            default="./wiki/Module:Characters/characters.json",
            help="Path to the existing JSON file containing character data.")
        parser.add_argument(
            "--output-file",
            action="store",
            default="./characters-new.json",
            help="Path to the output JSON file containing character data.")
        return parser

    def run_command(self):
        if (Path(self.parsed_args.output_file).exists()):
            raise Exception(f"{self.parsed_args.output_file} already exists, refusing to overwrite.")
        log.info(f"Loading input file {self.parsed_args.input_file}")
        self.print_n("Processing characters", end="", flush=True)
        chars = {}
        chars_orig = None
        new_chars = []
        with open(self.parsed_args.existing, "r") as existing_file:
            chars_orig = json.load(existing_file)
        with open(self.parsed_args.input_file, newline='') as csvfile:
            csvr = csv.reader(csvfile, delimiter=',', quotechar='"')
            columns = None
            cmap = {}
            for row in csvr:
                if columns == None:
                    columns = row
                    for ci, c in enumerate(columns):
                        cmap[str.lower(c)] = ci
                    log.info(f"Columns: {columns}")
                    continue
                pname = row[cmap["primary name"]]
                if str.lower(row[cmap["type"]]) != "primary":
                    self.print_v(f"Skipping non-primary row: {pname}")
                    continue
                if pname == "N/A":
                    pname = row[cmap["common name"]]
                self.print_n(f"Found character: {pname}")
                if pname in chars:
                    i = 1
                    pname = row[cmap["full name"]]
                    new_name = pname
                    while new_name in chars:
                        i += 1
                        new_name = pname + "(chardup" + str(i) + ")"
                    pname = new_name
                chars[pname] = {}
                if pname in chars_orig:
                    log.debug(f"Character {pname} already exists in existing JSON.")
                    chars[pname] = copy.deepcopy(chars_orig[pname])
                else:
                    self.print_n(f"New character: {pname}")
                    new_chars.append(pname)
                if chars[pname].get("name") != None and chars[pname]["name"] != pname:
                    raise Exception(f"Error: character {pname} has conflicting name in existing JSON: {chars[pname]['name']}")
                chars[pname]["name"] = pname
                chars[pname]["wot_character_names_data_v1_import"] = True
                species = row[cmap["species"]].lower()
                if species in [ "human", "horse", "wolf", "ogier", "lopar", "cat", "to'raken", "doll", "gholam", "dog", "s'redit", "trolloc", "raken", "myrddraal", "nym" ]:
                    if chars[pname].get(species) != None and chars[pname].get(species) != True:
                        raise Exception(f"Error: character {pname} has conflicting species in existing JSON: {chars[pname].get(species)} vs {species}")
                    chars[pname][species] = True
                elif species not in [ "n/a", "god", "giant" ]:
                    raise Exception(f"Error: character {pname} has unrecognized species: {species}")
                book = books.books_by_str[row[cmap["firsto"]].lower()].get("abbrev")
                if book == None:
                    raise Exception(f"Error: could not find book {row[cmap['firsto']]} in books data for character {pname}")
                first_name_occurrence = {
                    "book": book
                }
                if chars[pname].get("first_name_occurrence") != None and chars[pname].get("first_name_occurrence") != first_name_occurrence:
                    raise Exception(f"Error: character {pname} has conflicting first name occurrence in existing JSON: {chars[pname].get('first_name_occurrence')} vs {first_name_occurrence}")
                chars[pname]["first_name_occurrence"] = first_name_occurrence
                appears = row[cmap["appears"]]
                if chars[pname].get("appears") != None and chars[pname].get("appears") != appears:
                    raise Exception(f"Error: character {pname} has conflicting appears in existing JSON: {chars[pname].get('appears')} vs {appears}")
                chars[pname]["appears"] = appears
                gender = row[cmap["gender"]]
                sex = None
                if gender.lower() == "m":
                    sex = { "male": True, "female": False }
                elif gender.lower() == "f":
                    sex = { "male": False, "female": True }
                if sex != None:
                    if gender != None and (chars[pname].get("male", sex["male"]) != sex["male"] or chars[pname].get("female", sex["female"]) != sex["female"]):
                        raise Exception(f"Error: character {pname} has conflicting gender in existing JSON: {chars[pname].get('male')} vs {sex['male']}, {chars[pname].get('female')} vs {sex['female']}")
                    chars[pname]["male"] = sex["male"]
                    chars[pname]["female"] = sex["female"]
                dark = row[cmap["dark?"]]
                if dark == True:
                    if chars[pname].get("dark") != None and chars[pname].get("dark") != dark:
                        raise Exception(f"Error: character {pname} has conflicting dark in existing JSON: {chars[pname].get('dark')} vs {dark}")
                    chars[pname]["dark"] = dark
                # nation = row[cmap["nationality"]]
                birth = row[cmap["birth year"]]
                match = re.match(r"^(\d+)\s+([A-Z]+)$", birth)
                if match:
                    birth_year = int(match.group(1))
                    birth_calendar = match.group(2).upper()
                    if chars[pname].get("birth_year") == None:
                        chars[pname]["birth_year"] = {}
                    elif chars[pname]["birth_year"]["year"] != birth_year or chars[pname]["birth_year"]["calendar"] != birth_calendar:
                        raise Exception(f"Error: character {pname} has conflicting birth year in existing JSON: {chars[pname].get('birth_year')} vs {birth_year}")
                    chars[pname]["birth_year"]["year"] = birth_year
                    chars[pname]["birth_year"]["birth_calendar"] = birth_calendar
        for c in chars_orig:
            # TODO andrewf: Delete this; it was a one-time thing to initially fill in as a convenience.
            if c in chars:
                chars[c]["human"] = True
            else:
                chars_orig[c]["human"] = True
                chars[c] = chars_orig[c]
        self.print_n(f"Added {len(new_chars)} new characters.")
        self.print_v(f"Writing all characters to {self.parsed_args.output_file}")
        with open(self.parsed_args.output_file, "w") as f:
            json.dump(chars, f, indent=2, sort_keys=True)
        self.print_n(f"Wrote characters to {self.parsed_args.output_file}.")
        self.print_n(f"Done.")
        # if (self.parsed_args.verbosity == Verbosity.NORMAL):
        #     print("done", flush=True)
        # self.print_n(f"Wrote new characters to {self.parsed_args.output_file}.")
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