#!/usr/bin/env python3
# Copyright 2025 ncsuandrew12
# Modifications Copyright to their individual contributors
# Licensed under the Open Software License version 3.0
# SPDX-License-Identifier: OSL-3.0
"""
Theoryland Interview Database Processor

This script processes HTML files from the Theoryland Interview Database and converts
them into structured JSON and Markdown formats.

The script performs three main operations:
1. Normalizes raw HTML files for consistent formatting
2. Parses the normalized HTML to extract structured interview data
3. Generates JSON and Markdown output files

Dependencies:
    - beautifulsoup4: For HTML parsing and normalization
    - markdownify: For converting HTML content to Markdown

Author: ncsuandrew12
License: OSSL-3.0
"""

import argparse
import json
import logging
import os
import re
import sys

from datetime import datetime
from pathlib import Path
from bs4 import BeautifulSoup
from markdownify import markdownify as md

logger = logging.getLogger("tidbc")
logging.basicConfig(filename='tidbc.log', level=logging.INFO)
logger.addHandler(logging.StreamHandler(sys.stdout))

class SummaryField:
    """
    Represents a metadata field from an interview summary section.
    
    This class defines the structure and properties of fields that can appear
    in an interview's summary metadata.
    
    Attributes:
        required (bool): Whether this field is required to be present
        name (str): The field name as it appears in the HTML
        pyName (str): The Python property name (defaults to name if not specified)
        content: The extracted content of the field
        plainString (bool): Whether the field should be treated as plain text
    """
    required = None
    name = None
    pyName = None
    content = None
    plainString = None

    def __init__(self, name=None, pyName=None, required=True, plainString=False):
        """
        Initialize a SummaryField instance.
        
        Args:
            name (str, optional): The field name as it appears in HTML
            pyName (str, optional): The Python property name (defaults to name)
            required (bool): Whether this field is required (default: True)
            plainString (bool): Whether to treat as plain text (default: False)
        """
        self.required = required
        self.name = name
        self.pyName = pyName if pyName is not None else name
        self.plainString = plainString

    def __str__(self):
        return f"SummaryField: {self.toJSON()}"

    def toJSON(self):
        return json.dumps(self.__dict__, cls=JsonEncoder)

class Interview:
    """
    Represents a complete interview from the Theoryland Database.
    
    This class contains all the structured data for a single interview,
    including metadata and a list of interview entries.
    
    Attributes:
        id (int): Unique identifier for the interview
        title (str): Interview title
        entries (list[InterviewEntry]): List of Q&A entries in the interview
        entryCount (int): Number of entries in the interview
        date (datetime): Date of the interview
        entryType (str): Type of interview (e.g., "Book Signing", "Chat")
        location (str): Where the interview took place
        bookStore (str): Bookstore name if applicable
        tourCon (str): Tour or convention name if applicable
        reporter (str): Name of the person who conducted/reported the interview
        links (list): Related links for the interview
    """
    id = None
    title = None
    entries = None
    entryCount = None
    date = None
    entryType = None
    location = None
    bookStore = None
    tourCon = None
    reporter = None
    links = None
    
    def __str__(self):
        return f"Interview: {self.toJSON()}"
        
    def toJSON(self):
        return json.dumps(self.__dict__, cls=JsonEncoder)

class InterviewEntry:
    """
    Represents a single entry within an interview.
    
    Each entry typically contains content (the actual Q&A text converted
    to Markdown) and optional tags for categorization.
    
    Attributes:
        content (str): The entry content converted to Markdown format
        tags (list[str]): List of tags associated with this entry
    """
    content = None
    tags = []
    
    def __str__(self):
        return f"InterviewEntry: {self.toJSON()}"
        
    def toJSON(self):
        return json.dumps(self.__dict__, cls=JsonEncoder)

class JsonEncoder(json.JSONEncoder):
    """
    Custom JSON encoder for serializing Interview-related objects.
    
    This encoder handles the conversion of custom classes (SummaryField,
    Interview, InterviewEntry) and datetime objects to JSON-serializable
    formats.
    """
    def default(self, o):
        """
        Convert objects to JSON-serializable format.
        
        Args:
            o: Object to be serialized
            
        Returns:
            JSON-serializable representation of the object
        """
        if isinstance(o, SummaryField) or isinstance(o, Interview) or isinstance(o, InterviewEntry):
            return o.__dict__
        if isinstance(o, datetime):
            return datetime.strftime(o, '%Y-%m-%d')
        return super().default(o)

def main():
    """
    Main entry point for the HTML processing script.
    
    This function orchestrates the complete processing pipeline:
    1. Parses command line arguments
    2. Optionally normalizes raw HTML files
    3. Processes normalized HTML files to extract structured data
    4. Generates JSON output with all interview data
    5. Optionally generates Markdown files for documentation
    6. Optionally creates MediaWiki template for citations
    
    The function handles the workflow logic, determining what steps to execute
    based on command line flags and the presence of existing files.
    """
    parser = argparse.ArgumentParser(prog=__name__,
                                     description="Process raw HTML files from Theoryland Interview Database and translate them into more locally useful forms.")
    parser.add_argument('-r', '--raw-html-dir', type=str, help='Directory containing raw HTML files', default="./raw_html_downloads")
    parser.add_argument('-o', '--output-dir', type=str, help='Directory to save processed output files', default="../../docs/theoryland/interviews")
    parser.add_argument('-n', '--normalize', action='store_true', help='Normalize raw HTML files even if normalized files are present')
    parser.add_argument('-z', '--normalize-dir', type=str, help='Directory containing normalized HTML files', default="./norm_html")
    parser.add_argument('-j', '--load-json', action='store_true', help='(Not yet working) Load from existing JSON file instead of loading from normalized HTML files. Skips processing of raw and normalized HTML files')
    parser.add_argument('-k', '--skip-markdown', action='store_true', help='Skip generating Markdown files from the processed interviews')
    parser.add_argument('-t', '--mw-template-path', type=str, help='Path to the Mediawiki template for converting from id to citation description', default="./processed/mediawiki-template-tidb-switch.template")
    parser.add_argument('-l', '--log-level', type=int, help='Set the logging level')
    args = parser.parse_args()
    if args.log_level:
        logger.setLevel(args.log_level)
        print(f"Log level set to {args.log_level}")
    html_dir = Path(args.raw_html_dir)
    basename = "theoryland interview database"
    md_footer = f"## Contributing\n\n*If you are viewing this on github.io, you can see that this site is open source. Please do not try to improve this page. It is auto-generated by a python script. If you have suggestions for improvements, please start a discussion on [the github repo](https://source.wot.wiki) or [the Discord](https://discord.wot.wiki).*"
    normalize = args.normalize
    if args.load_json:
        normalize = False
    elif not normalize:
        p = Path(args.normalize_dir)
        normalized_files = list(p.glob("*.html")) + list(p.glob("*.htm"))
        normalize = len(normalized_files) == 0
    if normalize:
        logger.info("Checking for raw HTML files in directory:", html_dir)
        if not html_dir.exists():
            raise FileNotFoundError(f"Directory not found: {html_dir}")
        logger.info(f"Globbing HTML files in {html_dir}")
        html_files = list(html_dir.glob("*.html")) + list(html_dir.glob("*.htm"))
        if not html_files:
            logger.warning(f"No HTML files found in {html_dir}")
            return
        msg = f"Processing {len(html_files)} raw HTML files"
        logger.info(msg)
        if not logger.isEnabledFor(logging.DEBUG):
            print(msg, end='', flush=True)
        i = 0
        for f in html_files:
            normalize_raw_html(args, f)
            i += 1
            if not logger.isEnabledFor(logging.DEBUG) and i % 5 == 0:
                print(".", end='', flush=True)
        if not logger.isEnabledFor(logging.DEBUG):
            print("")
        p = Path(args.normalize_dir)
        normalized_files = list(p.glob("*.html")) + list(p.glob("*.htm"))
    json_path = Path(f"{args.output_dir}/{basename}.json")
    interviews = {}
    if not args.load_json:
        msg = f"Processing {len(normalized_files)} normalized HTML files"
        logger.info(msg)
        if not logger.isEnabledFor(logging.DEBUG):
            print(msg, end='', flush=True)
        for f in normalized_files:
            interview = process_html(args, f)
            interviews[str(interview.id)] = interview
            if not logger.isEnabledFor(logging.DEBUG) and len(interviews) % 5 == 0:
                print(".", end='', flush=True)
        if not logger.isEnabledFor(logging.DEBUG):
            print("")
        with open(json_path, 'w', encoding='utf-8') as f:
            logger.info(f"Writing JSON to {f.name}")
            f.write(json.dumps(interviews, cls=JsonEncoder, indent=2))
    # TODO Use beautifulsoup to convert our objects to HTML and compare against the (normalized) original HTML
    # as a verification of proper parsing.
    # with open(json_path, 'r', encoding='utf-8') as f:
    #     logger.info(f"Reading JSON from {f.name}")
    #     interviews = json.load(f)
    if not args.skip_markdown:
        with open(f"{args.output_dir}/theoryland interview database.md", 'w', encoding='utf-8') as m:
            msg = f"Writing Markdown to {m.name} and {args.output_dir}/t-*.md"
            logger.info(msg)
            if not logger.isEnabledFor(logging.DEBUG):
                print(msg, end='', flush=True)
            for i in range(1, len(interviews)+1):
                if not logger.isEnabledFor(logging.DEBUG) and i % 5 == 0:
                    print(".", end='', flush=True)
                with open(f"{args.output_dir}/t-{i}.md", 'w', encoding='utf-8') as p:
                    logger.debug(f"Writing interview Markdown to {p.name}")
                    interview = interviews[str(i)]
                    for f in [[m, "#"], [p, ""]]:
                        f[0].write(f"{f[1]}# [Interview #{interview.id}" + (f": {interview.title}" if interview.title else "") + f"](https://www.theoryland.com/intvmain.php?i={i})\n\n")
                        f[0].write(f"{f[1]}## Summary\n\n")
                    for f in [m, p]:
                        if interview.date:
                            f.write(f"- Date: {datetime.strftime(interview.date, '%Y-%m-%d')}\n\n")
                        if interview.entryType:
                            f.write(f"- Type: {interview.entryType}\n\n")
                        if interview.location:
                            f.write(f"- Location: {interview.location}\n\n")
                        if interview.bookStore:
                            f.write(f"- Bookstore: {interview.bookStore}\n\n")
                        if interview.tourCon:
                            f.write(f"- Tour/Con: {interview.tourCon}\n\n")
                        if interview.reporter:
                            f.write(f"- Reporter: {interview.reporter}\n\n")
                    if interview.links and len(interview.links) > 0:
                        p.write(f"### Links\n\n")
                        m.write(f"- Links:")
                        for link in interview.links:
                            p.write(f"- [" + (link['text'] if link['text'] else link['href']) + f"]({link['href']})\n\n")
                            m.write(f" [" + (link['text'] if link['text'] else link['href']) + f"]({link['href']})\n\n")
                        p.write("\n")
                        m.write("\n\n")
                    entry_i = 0
                    for entry in interview.entries:
                        entry_i += 1
                        ep = Path(f"{args.output_dir}/t-{i}/{entry_i}.md")
                        os.makedirs(ep.parent, exist_ok=True)
                        with open(ep, 'w', encoding='utf-8') as e:
                            logger.debug(f"Writing entry Markdown to {e.name}")
                            e.write(f"# [Interview #{interview.id}" + (f": {interview.title}" if interview.title else "") + f", Entry #{entry_i}](https://www.theoryland.com/intvmain.php?i={i}#{entry_i})\n\n")
                            e.write(entry.content + "\n\n")
                            e.write(md_footer)
                        for f in [m, p]:
                            f.write(f"## [Entry #{entry_i}](./t-{i}/{entry_i})\n\n")
                            f.write(entry.content + "\n\n")
                    for f in [m, p]:
                        f.write("\n---\n\n")
                    p.write(md_footer)
            m.write(md_footer)
            if not logger.isEnabledFor(logging.DEBUG):
                print("")
        with open(f"{args.output_dir}/index.md", 'w', encoding='utf-8') as f:
            logger.info(f"Writing interview index file to {f.name}")
            f.write("# [Theoryland Interview Database](https://www.theoryland.com/listintv.php)\n\n")
            f.write("This copy of the [Theoryland Interview Database](https://www.theoryland.com/listintv.php) is better suited for simple text searches and machine processing than the original. The original is more convenient for simple searches and has a bit of a prettier look.\n\n")
            f.write("All copyrights and licenses for the interviews belong to Theoryland or their original authors. We are not affiliated with Theoryland in any way.\n\n")
            f.write("## Downloads\n\n")
            f.write(f"* Full archive [JSON](./{basename}.json)\n\n")
            f.write(f"* Full archive [Markdown](./{basename}.md)\n\n")
            f.write("## Interviews\n\n")
            for i in range(1, len(interviews)+1):
                f.write(f"- [Interview #{i}" + (f": {interviews[str(i)].title}" if interviews[str(i)].title else "") + f"](./t-{i})" + "\n")
            f.write(md_footer)
    if args.mw_template_path:
        os.makedirs(os.path.dirname(args.mw_template_path), exist_ok=True)
        with open(args.mw_template_path, 'w', encoding='utf-8') as f:
            logger.info(f"Writing id-to-description mediawiki template switch code to {f.name}")
            f.write('<includeonly>{{TLlink|https://www.theoryland.com/intvmain.php?i&equals;{{{1}}}{{#if:{{{2|}}}|&#35;{{{2}}}}}|{{#if:{{{3|}}}|{{{3}}}|{{#switch:{{{1|}}}\n')
            ids = []
            for i in interviews.values():
                ids.append(i.id)
            ids.sort()
            missing = 0
            for id in ids:
                interview = interviews[str(id)]
                if not (interview.title or interview.date):
                    missing = missing + 1
                    continue
                title = interview.title
                if title is None:
                    title = interview.id
                line = f"  | {interview.id}={title}" + (f", {{{{Date|{datetime.strftime(interview.date, '%Y %b %d')}}}}}" if interview.date else "")
                f.write(line + "\n")
            f.write("""  | Theoryland Interview &#35;{{{1}}}}}}}{{#if:{{{2|}}}|&nbsp;- Q{{{2}}}}}}}</includeonly><noinclude>{{Documentation}}
[[Category:Utility templates]]</noinclude>\n""")
            logger.info(f"  Skipped {missing} entries with no title and no date")

def normalize_raw_html(args, file):
    """
    Normalize a raw HTML file using BeautifulSoup's prettify function.
    
    This function takes a raw HTML file and creates a normalized version
    with consistent formatting and structure. The normalized files are
    easier to parse reliably in subsequent processing steps.
    
    Args:
        args: Command line arguments object containing configuration
        file (Path): Path to the raw HTML file to normalize
        
    Note:
        The function writes the normalized HTML to the normalize_dir
        specified in the arguments, maintaining the same filename.
    """
    logger.debug(f"Normalizing raw HTML file {file}")
    # match = re.search(r'^(\d+)\.html{0,1}', os.path.basename(file))
    # if not match:
    #     raise RuntimeError(f"Filename does not match expected pattern: {file}")
    with open(file, 'r', encoding='utf-8') as f:
        html_content = f.read()
    soup = BeautifulSoup(html_content, 'html.parser')
    with open(os.path.join(args.normalize_dir, os.path.basename(file)), 'w', encoding='utf-8') as f:
        f.write(soup.prettify())

def process_html(args, file):
    """
    Process a normalized HTML file and extract structured interview data.
    
    This is the core parsing function that extracts all interview information
    from a normalized HTML file. It parses the specific HTML structure used
    by the Theoryland Interview Database and creates Interview objects with
    all metadata and entry content.
    
    The function expects a specific HTML structure:
    - A main body column containing interview content
    - An interview summary section with metadata fields
    - An entry list section with individual Q&A entries
    - Each entry contains an anchor, entry number, and entry data
    
    Args:
        args: Command line arguments object containing configuration
        file (Path): Path to the normalized HTML file to process
        
    Returns:
        Interview: A fully populated Interview object with all extracted data
        
    Raises:
        RuntimeError: If the HTML structure doesn't match expectations
        
    Note:
        The function performs extensive validation of the HTML structure
        and will raise detailed error messages if the format is unexpected.
    """
    logger.debug(f"Processing HTML file {file}")
    match = re.search(r'^(.+)\.html{0,1}$', os.path.basename(file))
    if not match:
        raise RuntimeError(f"Filename does not match expected pattern: {file}")
    result = Interview()
    interview_id = int(match.group(1))
    result.id = interview_id
    with open(os.path.join(args.normalize_dir, os.path.basename(file)), 'r', encoding='utf-8') as f:
        html_content = f.read()
    soup = BeautifulSoup(html_content, 'html.parser')
    main_columns = soup.find_all('div', class_='body-column-main')
    if len(main_columns) != 1:
        raise RuntimeError(f"Expected exactly one main body column in file {file}, found {len(main_columns)}")
    container_cols = list(main_columns)[0].find_all('div', class_='col-container', recursive=False)
    if len(container_cols) != 1:
        raise RuntimeError(f"Expected exactly one col-container in file {file}, found {len(container_cols)}")
    content_cols = list(container_cols)[0].find_all('div', class_='col-content', recursive=False)
    if len(content_cols) != 1:
        raise RuntimeError(f"Expected exactly one col-content in file {file}, found {len(content_cols)}")
    content_divs = list(content_cols)[0].find_all('div', recursive=False)
    if len(content_divs) != 2:
        raise RuntimeError(f"Expected exactly two col-content child divs in file {file}, found {len(content_divs)}: {content_divs}")
    content_div = list(content_divs)[1]
    if content_divs[1].attrs["style"] != "position:relative;":
        raise RuntimeError(f"Expected div to have style 'position:relative;' in file {file}, found {content_div.attrs}")
    summary = content_div.find_all('div', class_='intv-summary', recursive=False)
    if len(summary) != 1:
        raise RuntimeError(f"Expected exactly one div.intv-summary in file {file}, found {len(summary)}")

    logger.debug(f"Parsing summary for file {file}")
    summary = list(summary)[0]
    logger.debug(f"Summary: {summary}")
    summary_ch = summary.children
    
    # Define the expected metadata fields and their properties
    field_list = [ SummaryField(name="entries", pyName="entryCount", required=True), SummaryField(name="date", required=False),
        SummaryField(name="type", pyName="entryType", required=False, plainString=True), SummaryField(name="location", required=False, plainString=True),
        SummaryField(name="bookstore", required=False, plainString=True), SummaryField(name="tourcon", required=False, plainString=True),
        SummaryField(name="reporter", required=False, plainString=True), SummaryField(name="links", required=False) ]
    field_set = {}
    for field in field_list:
        field_set[field.name] = field
    fields = {}
    mode = None  # Current parsing mode (field name)
    mode_h4 = None  # The h4 element that started current mode
    field_key = None  # Current field key being processed
    extra_paragraphs = []  # Collect extra paragraphs for processing
    
    # Parse summary section children to extract metadata fields
    for child in summary_ch:
        logger.debug(f"Summary child: {child}")
        if child.name == 'h4':
            if not child.string:
                raise RuntimeError(f"Unexpected empty h4 in file {file}: {summary}")
            mode = child.string.strip().lower()
            logger.debug(f"Switching to {mode} mode")
            mode_h4 = child
            field_key = mode_h4.string.strip().lower()
        elif mode == None:
            if child.name == 'h3' or (child.name is None and str(child).strip() == ''):
                continue
            raise RuntimeError(f"Unexpected content {child} in summary before any h4 in file {file}: {summary}")
        elif mode == "links":
            logger.debug(f"Child links found")
            if not field_key in fields.keys():
                fields[field_key] = []
            if child.name == None:
                continue
            elif child.name == 'p':
                fields[field_key].append(child)
            else:
                raise RuntimeError(f"Unexpected content {child.name} in links section in file {file}: {summary}")
        else:
            if child.name == 'p':
                if field_key in field_set.keys():
                    if field_key in fields.keys():
                        extra_paragraphs.append(child)
                        continue
                    c = len(list(child.children))
                    if c == 0:
                        continue
                    if c != 1:
                        raise RuntimeError(f"Unexpected child count {c} for {field_key} paragraph found in file {file}: (mode {mode}) {child}")
                    fields[field_key] = list(child.children)[0].string
            elif child.name is None and str(child).strip() == '':
                continue
            else:
                raise RuntimeError(f"Unexpected content {child.name} in summary in file {file}: {summary}")
    logger.debug(f"Parsing extra paragraphs for file {file} (id={result.id})")
    for par in extra_paragraphs:
        logger.debug(f"{file} (id={result.id}): {par}")
        parchildren = list(par.children)
        if par.name == 'p':
            for parchild in parchildren:
                if parchild.name == None and str(parchild).strip() == '':
                    continue
                if parchild.name == 'a':
                    if 'links' not in fields.keys():
                        fields['links'] = []
                    fields['links'].append(parchild)
                else:
                    raise RuntimeError(f"Unexpected summary paragraphs found in file {file}: {par} {summary}")
        else:
            raise RuntimeError(f"Extra summary paragraphs found in file {file}: {par} {summary}")
    for field in field_list:
        if field.name not in fields.keys():
            if field.required:
                raise RuntimeError(f"Required field {field.name} not found in file {file}: {summary}")
            continue
    for k, v in fields.items():
        field = field_set[k]
        if field.plainString:
            result.__dict__[field.pyName] = v.string.strip()
        else:
            result.__dict__[field.pyName] = v
    result.entryCount = int(result.entryCount.string.strip())
    date = result.date
    result.date = None
    if date and date.string and date.string.strip() != '':
        date = re.sub(r'(\d+)[a-z]{2}, ', '\\1, ', date.string.strip()) # Remove 1st, 2nd, 3rd, 4th, etc.
        for datef in {'%b %d, %Y', '%b, %Y', '%Y'}:
            try:
                result.date = datetime.strptime(date, datef)
                break
            except ValueError as ve:
                continue
        if not result.date:
            raise RuntimeError(f"Date format not recognized in file {file}: {date}")
    if result.links:
        links_a = []
        for link in result.links:
            if link.name == 'p':
                for a in link.children:
                    if a.name == 'a':
                        links_a.append(a)
                    elif a.name == None and (a.string == None or a.string.strip() == ''):
                        continue
                    else:
                        raise RuntimeError(f"non-a 'link' in file {file}: {a}")
            elif link.name == 'a':
                links_a.append(link)
            elif link.name == None and (link.string == None or link.string.strip() == ''):
                continue
            else:
                raise RuntimeError(f"non-ap link in file {file}: {link}")
        links = []
        for link in links_a:
            if not link.string:
                logger.warning(f"Link with no text found in file {file}: {link}")
            if 'href' not in link.attrs:
                raise RuntimeError(f"Link with no href found in file {file}: {result.links}")
            links.append({"href": link.attrs['href'], "text": link.string.strip() if link.string else ""})

        result.links = links

    header_s = content_div.find_all('h3', recursive=False)
    if len(header_s) != 1:
        raise RuntimeError(f"Expected exactly one h3 in div.intv-summary in file {file}, found {len(header_s)}")
    header_c_iter = iter(list(header_s)[0].children)
    header_c = next(header_c_iter)
    if header_c.name == None and (header_c.string == None or header_c.string.strip() == ''):
        header_c = next(header_c_iter)
    if header_c.name == 'a' and (header_c.string == None or header_c.string.strip() == 'Interviews'):
        header_c = next(header_c_iter)
    if header_c.name == None and (header_c.string == None or header_c.string.strip() == ''):
        header_c = next(header_c_iter)
    if header_c.name == None and (header_c.string != None and header_c.string.strip() != ''):
        title = re.sub(r'^:\s*', '', header_c.string.strip())
        if len(title) > 0:
            result.title = title
    else:
        raise RuntimeError(f"Unexpected header structure in file {file}, {header_c}")

    entry_list_div = content_div.find_all('div', class_='intv-entry-list', recursive=False)
    if len(entry_list_div) != 1:
        raise RuntimeError(f"Expected exactly one div.intv-entry-list in file {file}, found {len(entry_list_div)}")
    entry_list_ul = list(entry_list_div)[0].find_all('ul', recursive=False)
    if len(entry_list_ul) != 1:
        raise RuntimeError(f"Expected exactly one entry list ul in file {file}, found {len(entry_list_ul)}")
    result.entries = []

    logger.debug(f"Parsing summary for file {file}")
    for entry_li in entry_list_ul[0].children:
        if entry_li.name == 'li':
            result.entries.append(InterviewEntry())
            entry_li_iter = iter(entry_li.children)
            entry_li_c = next(entry_li_iter)
            # Skip all empty text nodes
            if entry_li_c.name == None and (entry_li_c.string == None or entry_li_c.string.strip() == ''):
                entry_li_c = next(entry_li_iter)
            if entry_li_c.name == 'a':
                if 'href' not in entry_li_c.attrs:
                    if 'name' in entry_li_c.attrs:
                        if len(result.entries) != int(entry_li_c.attrs['name'].strip()):
                            raise RuntimeError(f"Entry li.a with unexpected name found in file {file}: {entry_li_c.attrs}")
                    else:
                        raise RuntimeError(f"Entry li.a with no href or name found in file {file}: {entry_li}")
                else:
                    raise RuntimeError(f"Entry li.a with href found in file {file}: {entry_li}")
            else:
                raise RuntimeError(f"Entry li[0] with unexpected name {entry_li_c.name} found in file {file}: {entry_li_c}")
            entry_li_c = next(entry_li_iter)
            # Skip all empty text nodes
            if entry_li_c.name == None and (entry_li_c.string == None or entry_li_c.string.strip() == ''):
                entry_li_c = next(entry_li_iter)
            # logger.debug(f"entry-num div expected: in {file}: {entry_li_c}")
            # logger.debug(f"{entry_li_c.name} {entry_li_c.attrs} {entry_li_c.attrs['class']}")
            if entry_li_c.name == 'div' and 'class' in entry_li_c.attrs and len(entry_li_c.attrs['class']) == 1 and entry_li_c.attrs['class'][0] == 'entry-num':
                entry_li_c_children = list(entry_li_c.children)
                if len(entry_li_c_children) != 3:
                    raise RuntimeError(f"Entry li.div<entry-num> with unexpected children found in file {file}: {entry_li}")
                if entry_li_c_children[1].name == 'p':
                    entry_li_p_children = list(entry_li_c_children[1].children)
                    if len(entry_li_p_children) != 1:
                        raise RuntimeError(f"Entry li.div<entry-num>.p with unexpected children found in file {file}: {entry_li}")
                    if len(result.entries) != int(entry_li_p_children[0].string.strip()):
                        raise RuntimeError(f"Entry li.div<entry-num>.p with unexpected number found in file {file}: {entry_li}")
                else:
                    raise RuntimeError(f"Entry li.div<entry-num> with no p child found in file {file}: {entry_li}")
            else:
                raise RuntimeError(f"Entry li[1] with unexpected name {entry_li_c.name} found in file {file}: {entry_li_c}")
            entry_li_c = next(entry_li_iter)
            # Skip all empty text nodes
            if entry_li_c.name == None and (entry_li_c.string == None or entry_li_c.string.strip() == ''):
                entry_li_c = next(entry_li_iter)
            if entry_li_c.name == 'div' and 'class' in entry_li_c.attrs and len(entry_li_c.attrs['class']) == 1 and entry_li_c.attrs['class'][0] == 'entry-data':
                mode = None
                for entry_data_c in entry_li_c.children:
                    if entry_data_c.name == 'h4' and entry_data_c.string and entry_data_c.string.strip() == 'Tags':
                        mode = "tags"
                        entry_data_c.extract()
                        continue
                    if mode == "tags":
                        entry_data_c.extract()
                        if entry_data_c.name == None and (entry_data_c.string == None or entry_data_c.string.strip() == ''):
                            continue
                        if entry_data_c.name != 'div':
                            raise RuntimeError(f"Entry li.div<entry-data>.h4 Tags not followed by div in file {file}: {entry_data_c.name}: {entry_data_c}")
                        for tag_form in entry_data_c.children:
                            if tag_form.name == None and (tag_form.string == None or tag_form.string.strip() == '' or tag_form.string.strip() == ','):
                                continue
                            if tag_form.name != 'form':
                                raise RuntimeError(f"Entry li.div<entry-data>.h4 Tags not followed by div.form in file {file}: {tag_form}")
                            tag_buttons = tag_form.find_all('button', recursive=False)
                            for tag_button in tag_buttons:
                                if 'class' not in tag_button.attrs or len(tag_button.attrs['class']) != 1 or tag_button.attrs['class'][0] != 'lk-search-tag':
                                    raise RuntimeError(f"Entry li.div<entry-data>.h4 Tags div.form contains non-lk-search-tag button in file {file}: {tag_button}")
                                result.entries[len(result.entries)-1].tags.append(tag_button.text.strip())
                result.entries[len(result.entries)-1].content = md(str(entry_li_c))
            else:
                raise RuntimeError(f"Entry li[2] with unexpected name {entry_li_c.name} found in file {file}: {entry_li}")
            entry_li_c = next(entry_li.children)
            if entry_li_c and entry_li_c.name == None and (entry_li_c.string == None or entry_li_c.string.strip() == ''):
                entry_li_c = next(entry_li.children)
        elif entry_li.name == None and (entry_li.string == None or entry_li.string.strip() == ''):
            continue
        else:
            raise RuntimeError(f"Non-li element in entry list in file {file}: {entry_li}")

    logger.debug(f"Processed file {file}")
    logger.debug(f"Result: {result}")
    return result

if __name__ == "__main__":
    main()