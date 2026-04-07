import argparse
import json
import sys
import re
from command import Command, Progresser, Verbosity, run_command
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
            action="append",
            default=None,
            help="Path to an input JSON file containing character data.")
        parser.add_argument(
            "--output-file",
            action="store",
            default="./characters.json",
            help="Path to the output JSON file containing character data.")
        return parser

    def run_command(self):
        if (Path(self.parsed_args.output_file).exists()):
            raise Exception(f"{self.parsed_args.output_file} already exists, refusing to overwrite.");
        d = {}
        log.info(f"Loading input files {self.parsed_args.input_file}")
        progressor = Progresser(self)
        for input_file in self.parsed_args.input_file:
            progressor.tick()
            input = json.load(open(input_file, "r"))
            d = d | input
        with open(self.parsed_args.output_file, "w") as f:
            json.dump(d, f, indent=2, sort_keys=True)
        self.print_n(f"Wrote {len(d)} entries to {self.parsed_args.output_file}.")
        if (self.parsed_args.verbosity >= Verbosity.APPVERBOSE):
            with open(self.parsed_args.output_file, "r") as f:
                for line in f:
                    self.print_v(line, end="", flush=True)
        return 0

exit(run_command(ConvertTsvCharactersToJson(sys.argv)))