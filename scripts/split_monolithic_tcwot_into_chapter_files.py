import argparse
import json
import re
import sys
from command import Command, Verbosity, run_command
# from log_utils import logger as log
from pathlib import Path

class SplitTcwot(Command):
    expected_separators = [' ', '   ', '*  *  *', '*   *   *']

    def __init__(self, args):
        Command.__init__(self, args)

    def create_arg_parser(self):
        parser = argparse.ArgumentParser(
            description="Split The Complete Wheel of Time omnibus (in wotsauce JSON form) into individual chapter files."
        )
        parser.add_argument(
            "--input",
            action="store",
            default="../wotwiki-secret/source material/the-complete-wheel-of-time.json",
            help="Path to the input JSON file.")
        parser.add_argument(
            "--outdir-json",
            action="store",
            default="../wotwiki-secret/source material/novels-json",
            help="Directory for the per-chapter JSON output files.")
        parser.add_argument(
            "--outdir-md",
            action="store",
            default="../wotwiki-secret/source material/novels-md",
            help="Directory for the per-chapter Markdown output files.")
        return parser

    def warn(self, message):
        self.print(Verbosity.APPQUIET, message)

    def sanitize_str_for_filename(self, s):
        s = re.sub(r"\s+", "_", s)
        s = re.sub(r"\u2019", "", s)
        s = re.sub(r"[^a-zA-Z0-9_\-]", "", s)
        s = re.sub(r"_+", "_", s)
        return s

    def run_command(self):
        data = None
        self.print_n(f"Loading input file {self.parsed_args.input}")
        with open(self.parsed_args.input, "r") as f:
            data = json.load(f)
        for book_index, book in enumerate(data["BookCollection"]["Book"]):
            title = book['title']
            book_title_n = self.sanitize_str_for_filename(title.strip().lower())
            filename_book_base = f"{book_index:02d}-{book_title_n}"
            filename_book_md = f"{self.parsed_args.outdir_md}/{filename_book_base}/{filename_book_base}.md"
            self.print_n(f"Processing {title}: {filename_book_md}")
            Path(filename_book_md).parent.mkdir(parents=True, exist_ok=True)
            with open(filename_book_md, "w") as f_md:
                f_md.write(f"# {title}\n\n")
                for key in ["Intro", "Prologue", "Epilogue", "Outro", "Foreword", "Glossary"]:
                    if (key in book) and (len(book[key]["sections"]) != 1):
                        raise Exception(f"Error: non-1 section length for chapter {title}: {key}")
                for key in book:
                    if key not in ["title", "Chapter", "Intro", "Foreword", "Prologue", "Epilogue", "Glossary", "Outro"]:
                        raise Exception(f"Error: unexpected key in book {title}: {key}")
                for sect_key in ["Intro", "Foreword", "Prologue"]:
                    if sect_key in book:
                        self.process_chapter(book_index, title, filename_book_base, f_md, "00-", book[sect_key]["title"], book[sect_key]["sections"][0]["parts"])
                chapter_cnt = 0
                for chapter in book["Chapter"]:
                    chapter_title = chapter["title"]
                    chapter_num = int(chapter["num"])
                    if chapter_num > chapter_cnt:
                        chapter_cnt = chapter_num
                    if len(chapter["sections"]) != 1:
                        raise Exception(f"Error: non-1 section length for chapter {title}: {chapter_num}: {chapter_title}")
                    self.process_chapter(book_index, title, filename_book_base, f_md, f"{chapter_num:02d}-", chapter_title, chapter["sections"][0]["parts"])
                for sect_key in ["Epilogue", "Glossary", "Outro"]:
                    if sect_key in book:
                        chapter_cnt += 1
                        self.process_chapter(book_index, title, filename_book_base, f_md, f"{chapter_cnt:02d}-", book[sect_key]["title"], book[sect_key]["sections"][0]["parts"])
        self.print_n("Done.")
        return 0

    def process_chapter(self, book_index, book_title, filename_book_base, f_book_md, filename_prefix, title, parts):
        title_n = self.sanitize_str_for_filename(title.strip().lower())
        filename_base = f"{filename_book_base}/{filename_book_base}-{filename_prefix}{title_n}"
        filename_json = f"{self.parsed_args.outdir_json}/{filename_base}.json"
        filename_chapter_md = f"{self.parsed_args.outdir_md}/{filename_base}.md"
        self.print_v(f"{book_index:02d}: {book_title}: {title:30s} - {filename_chapter_md}")
        for filename in [ filename_json, filename_chapter_md ]:
            Path(filename).parent.mkdir(parents=True, exist_ok=True)
        with open(filename_json, "w") as f_json, open(filename_chapter_md, "w") as f_md:
            chapter_out = []
            f_md.write(f"# {title}\n\n")
            f_book_md.write(f"## {title}\n\n")
            for part in parts:
                type = part["type"]
                if type == "BookSegmentSectionPartParagraph":
                    for key in part:
                        if key not in ["type", "text", "leading"]:
                            raise Exception(f"Error: unexpected key in BookSegmentSectionPartParagraph: {book_title}: {title}: {part}")
                    if "leading" in part:
                        for leading_part in part["leading"]:
                            for key in leading_part:
                                if key not in ["type", "text"]:
                                    raise Exception(f"Error: expected key missing from BookSegmentSectionPartParagraph: {book_title}: {title}: {key}: {leading_part}")
                            if leading_part["type"] != "BookSegmentSectionPartSeparator":
                                raise Exception(f"Error: unexpected leading content in part: {book_title}: {title}: {leading_part}")
                            if not leading_part["text"] in self.expected_separators:
                                self.warn(f"Warning: unexpected leading content in part: {book_title}: {title}: '{leading_part['text']}': {self.expected_separators}")
                            chapter_out.append(leading_part['text'])
                            for f in [f_md, f_book_md]:
                                f.write(f"{leading_part['text']}\n\n")
                    chapter_out.append(part["text"])
                    for f in [f_md, f_book_md]:
                        f.write(part["text"] + "\n\n")
                elif type == "GlossaryEntry":
                    for key in part:
                        if key not in ["type", "text", "leading", "ipa", "displayName", "parts", "name"]:
                            raise Exception(f"Error: unexpected key in BookSegmentSectionPartParagraph: {book_title}: {title}: {key}: {part}")
                    if "leading" in part:
                        for leading_part in part["leading"]:
                            for key in leading_part:
                                if key not in ["type", "text"]:
                                    raise Exception(f"Error: expected key missing from BookSegmentSectionPartParagraph: {book_title}: {title}: {key}: {leading_part}")
                            if leading_part["type"] != "BookSegmentSectionPartSeparator":
                                raise Exception(f"Error: unexpected leading content in part: {book_title}: {title}: {leading_part}")
                            if not leading_part["text"] in self.expected_separators:
                                self.warn(f"Warning: unexpected leading content in part: {book_title}: {title}: '{leading_part['text']}': {self.expected_separators}")
                            chapter_out.append(leading_part['text'])
                            for f in [f_md, f_book_md]:
                                f.write(f"{leading_part['text']}\n\n")
                    chapter_out.append(part)
                    if "text" in part:
                        for key in part:
                            if key not in ["type", "text"]:
                                raise Exception(f"Error: unexpected key in BookSegmentSectionPartParagraph: {book_title}: {title}: {key}: {part}")
                        for f in [f_md, f_book_md]:
                            f.write(f"{part['text']}\n\n")
                    else:
                        for key in part:
                            if key not in ["type", "displayName", "ipa", "parts", "name", "leading"]:
                                raise Exception(f"Error: unexpected key in BookSegmentSectionPartParagraph: {book_title}: {title}: {key}: {part}")
                        postName=""
                        if "ipa" in part:
                            postName = f" ({part['ipa']}): "
                        else:
                            postName = " - "
                        for f in [f_md, f_book_md]:
                            f.write(f"{part['displayName']}{postName}")
                        for subpart in part["parts"]:
                            if subpart["type"] != "BookSegmentSectionPartParagraph":
                                raise Exception(f"Error: unexpected type in GlossaryEntry subpart: {subpart}")
                            for key in subpart:
                                if key not in ["type", "text"]:
                                    raise Exception(f"Error: unexpected key in GlossaryEntryPartParagraph: {subpart}")
                            for f in [f_md, f_book_md]:
                                f.write(f"{subpart['text']}\n\n")
                else:
                    raise Exception(f"Error: type is {type}")
            json.dump(chapter_out, f_json, indent=2, sort_keys=False)

exit(run_command(SplitTcwot(sys.argv)))