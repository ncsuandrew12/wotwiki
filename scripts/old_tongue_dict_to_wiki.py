import argparse
import json
import sys
import re
from command import Command, CommandProgresser,  run_command
from log_utils import logger as log
from pathlib import Path

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
            default="../wotwiki/source-material/companion-old-tongue.md",
            help="Path to the input Markdown file containing the Old Tongue dictionary.")
        parser.add_argument(
            "--out-json",
            action="store",
            default="../wotwiki/source-material/companion-old-tongue.json",
            help="Path to the output JSON file.")
        parser.add_argument(
            "--overwrite-out-json",
            action="store_true",
            help="Overwrite the output JSON file.")
        return parser

    def add_entry(self, entries, sub_entry):
        if sub_entry["word"] in entries:
            entries[sub_entry["word"]].append(sub_entry)
        else:
            entries[sub_entry["word"]] = [sub_entry]

    def finish_sub_entry(self, entries, sub_entry):
        try:
            log.debug(f"Finishing sub_entry: {sub_entry}")
            new_entries = []
            r = r"(.*)(?<!e\.g\., )(?<!e\.g\., in )\[([^\/\]]+)-*\](?>! = )-*(\([^\)]+\)){0,1}\s*(\S.*)"
            match = re.match(r, sub_entry["definition"]["companion_epub_md"])
            while match:
                word = match.group(2)
                if word in entries:
                    match = None
                    continue
                log.debug("Contains another sub_entry")
                sub_entry["definition"]["companion_epub_md"] = re.sub(r"\s*;*\s*$", "", re.sub(r, r"\1", sub_entry["definition"]["companion_epub_md"], count=1))
                ne = { "word": word, "definition": { "companion_epub_md": match.group(4) } }
                if len(match.group(3) or "") > 2:
                    ne["parts"] = match.group(3)[1:-1]
                elif "parts" in sub_entry:
                    ne["parts"] = sub_entry["parts"]
                elif "ref" in sub_entry:
                    ne["ref"] = sub_entry["ref"]
                self.add_entry(entries, sub_entry)
                new_entries.append(ne)
                match = re.match(r, sub_entry["definition"]["companion_epub_md"])
            for sub_entry in new_entries:
                self.add_entry(entries, sub_entry)
                self.finish_sub_entry(entries, sub_entry)
            sub_entry["definition"]["companion_epub_md"] = re.sub(r"^=\s*, ", "", sub_entry["definition"]["companion_epub_md"])
            sub_entry["definition"]["companion"] = re.sub(r"[\[\]]", "", sub_entry["definition"]["companion_epub_md"])
            sub_entry["definition"]["wotwiki"] = re.sub(r"\[", r"<i>[[",
                re.sub(r"\]", r"]]</i>",
                       re.sub(r"\[([^/\]]+)\/([^\]]+)\]", r"[\1]/[\2]", sub_entry["definition"]["companion_epub_md"])))
            if "parts" in sub_entry:
                sub_entry["parts_companion"] = sub_entry["parts"]
                if type(sub_entry["parts"]) == str:
                    if sub_entry["parts"] == "complex word form":
                        sub_entry["parts"] = [ { "type": "complex word form" } ]
                    else:
                        sub_entry["parts"] = re.sub(r"[\s&,]+", ";",
                            re.sub("generally ", "generally_",
                            re.sub(" aux", "_aux",
                            re.sub(" neg", "_neg",
                            re.sub("past part", "past_part",
                            re.sub("rel pron", "rel_pron",
                            re.sub("poss pron", "poss_pron",
                            re.sub(r"[\.]", "", sub_entry["parts"])))))))).split(";")
                        for i, part in enumerate(sub_entry["parts"]):
                            modifiers = []
                            if part.startswith("generally_"):
                                part = part[len("generally_"):]
                                modifiers.append("generally")
                            if part.endswith("_aux"):
                                part = part[:-len("_aux")]
                                modifiers.append("auxilliary")
                            if part.endswith("_neg"):
                                part = part[:-len("_neg")]
                                modifiers.append("negative")
                            if part == "adj":
                                sub_entry["parts"][i] = "adjective"
                            elif part == "adv":
                                sub_entry["parts"][i] = "adverb"
                            elif part == "comb":
                                sub_entry["parts"][i] = "combination"
                            elif part == "conj":
                                sub_entry["parts"][i] = "conjunction"
                            elif part == "interjection":
                                pass
                            elif part == "n":
                                sub_entry["parts"][i] = "noun"
                            elif part == "past_part":
                                sub_entry["parts"][i] = "past participle"
                            elif part == "poss_pron":
                                sub_entry["parts"][i] = "possessive pronoun"
                            elif part == "prefix":
                                sub_entry["parts"][i] = "prefix"
                            elif part == "prep":
                                sub_entry["parts"][i] = "preposition"
                            elif part == "pron":
                                sub_entry["parts"][i] = "pronoun"
                            elif part == "rel_pron":
                                sub_entry["parts"][i] = "relative pronoun"
                            elif part == "v":
                                sub_entry["parts"][i] = "verb"
                            elif part == "suffix":
                                sub_entry["parts"][i] = "suffix"
                            else:
                                raise Exception(f"Error: unrecognized part of speech: {part}")
                            sub_entry["parts"][i] = { "type": sub_entry["parts"][i] }
                            if len(modifiers) > 0:
                                sub_entry["parts"][i]["modifiers"] = modifiers
        except Exception as e:
            log.error(f"Error processing sub_entry {sub_entry['word']}: {e}")
            raise Exception(f"Error processing sub_entry {sub_entry['word']}: {sub_entry} {e}")

    def run_command(self):
        if (not self.parsed_args.overwrite_out_json and Path(self.parsed_args.out_json).exists()):
            raise Exception(f"{self.parsed_args.out_json} already exists, refusing to overwrite.")
        log.info(f"Loading input file {self.parsed_args.input_file}")
        self.print_n("Processing word lines", end="", flush=True)
        entries = {}
        sub_entry = None
        progresser = CommandProgresser(self, period=1)
        with open(self.parsed_args.input_file, "r") as input_f:
            for line in input_f:
                line = line.strip()
                log.debug(f"line: {line}")
                progresser.tick()
                if line == "":
                    # if sub_entry:
                    #     self.add_entry(entries, sub_entry)
                    sub_entry = None
                elif sub_entry == None:
                    match = re.match(r'^\[{0,1}([^\]]+)\]{0,1}---\]{0,1}(\([^\)]+\)){0,1}\s*(\S.*)$', line)
                    if not match:
                        raise Exception(f"Error: unrecognized entry format: {line}")
                    sub_entry = { "word": match.group(1), "definition": { "companion_epub_md": match.group(3) } }
                    if len(match.group(2) or "") > 2:
                        sub_entry["parts"] = match.group(2)[1:-1]
                    sub_entry["refs"] = [{ "book": "twotc", "entry": "otdict", "word": sub_entry["word"] }]
                    self.add_entry(entries, sub_entry)
                else:
                    sub_entry["definition"]["companion_epub_md"] += " " + line
        progresser.done()
        progresser.restart()
        self.print_n("Checking entries for inline definitions and performing other post-processing", end="", flush=True)
        unprocessed = entries.copy()
        for _, entry in unprocessed.items():
            progresser.tick()
            print(".", end="", flush=True)
            for sub_entry in entry:
                self.finish_sub_entry(entries, sub_entry)
        for _, entry in entries.items():
            word = entry[0]["word"]
            log.debug(f"Final processing for entry: {entry}")
            for se in entry:
                d = se["definition"]
                if d["companion"] == d["companion_epub_md"]:
                    del d["companion"]
                if "companion" in d and d["companion"] == d["wotwiki"]:
                    del d["wotwiki"]
                if "wotwiki" in d and d["wotwiki"] == d["companion_epub_md"]:
                    del d["wotwiki"]
            if len(entry) == 1:
                entries[word] = entry[0]
            else:
                ne = { "word": entry[0]["word"], "entries": entry, "refs": [] }
                for sub_entry in ne["entries"]:
                    log.debug(f"Final processing for sub_entry: {sub_entry}")
                    if sub_entry["word"] != ne["word"]:
                        raise Exception(f"Error: sub_entry word {sub_entry['word']} does not match entry word {ne['word']}")
                    del sub_entry["word"]
                    for ref in sub_entry["refs"]:
                        ne["refs"].append(ref)
                    del sub_entry["refs"]
                if len(ne["refs"]) < 1:
                    del ne["refs"]
                entries[word] = ne
            if word == "Tarmon Gai'don":
                entries[word]["italicize"] = False
        progresser.done()
        self.print_v(f"Parsed {len(entries)} entries. Writing to {self.parsed_args.out_json}...", end="", flush=True)
        with open(self.parsed_args.out_json, "w") as f:
            json.dump(entries, f, indent=2, sort_keys=True)
        self.print_v("done", flush=True)
        self.print_n(f"Wrote {len(entries)} entries to {self.parsed_args.out_json}.")
        return 0

exit(run_command(ConvertOtDictToWiki(sys.argv)))