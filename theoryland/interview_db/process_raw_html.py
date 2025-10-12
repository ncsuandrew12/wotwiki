#!/usr/bin/env python3
"""
Script to extract h3 elements containing links to listintv.php from HTML files
in the theoryland interview database raw html directory.
"""

import os
import re
import json
from datetime import datetime
from pathlib import Path
from bs4 import BeautifulSoup

class SummaryField:
    required = None
    name = None
    pyName = None
    content = None
    plainString = None
    def __init__(self, name=None, pyName=None, required=True, plainString=False):
        self.required = required
        self.name = name
        self.pyName = pyName if pyName is not None else name
        self.plainString = plainString
    def __str__(self):
        return f"SummaryField: {self.toJSON()}"
    def toJSON(self):
        return json.dumps(self.__dict__, cls=JsonEncoder)

class Interview:
    id = None
    title = None
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

class JsonEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, SummaryField) or isinstance(o, Interview):
            return o.__dict__
        if isinstance(o, datetime):
            return datetime.strftime(o, '%Y-%m-%d')
        return super().default(o)

def process_raw_html(file):
    """
    Find h3 elements that contain an 'a' element with href='listintv.php'
    Returns the full content of such h3 elements.
    """

    match = re.search(r'^(\d+)\.html{0,1}', os.path.basename(file))
    if not match:
        raise ValueError(f"Filename does not match expected pattern: {file}")

    result = Interview()

    interview_id = int(match.group(1))
    result.id = interview_id

    with open(file, 'r', encoding='utf-8', errors='ignore') as f:
        html_content = f.read()
    soup = BeautifulSoup(html_content, 'html.parser')

    with open("./norm_html/" + os.path.basename(file), 'w', encoding='utf-8', errors='ignore') as f:
        f.write(soup.prettify())

    main_columns = soup.find_all('div', class_='body-column-main')
    if len(main_columns) != 1:
        raise ValueError(f"Expected exactly one main body column in file {file}, found {len(main_columns)}")
    container_cols = list(main_columns)[0].find_all('div', class_='col-container', recursive=False)
    if len(container_cols) != 1:
        raise ValueError(f"Expected exactly one col-container in file {file}, found {len(container_cols)}")
    content_cols = list(container_cols)[0].find_all('div', class_='col-content', recursive=False)
    if len(content_cols) != 1:
        raise ValueError(f"Expected exactly one col-content in file {file}, found {len(content_cols)}")
    content_divs = list(content_cols)[0].find_all('div', recursive=False)
    if len(content_divs) != 2:
        raise ValueError(f"Expected exactly two col-content child divs in file {file}, found {len(content_divs)}: {content_divs}")
    if content_divs[1].attrs["style"] != "position:relative;":
        raise ValueError(f"Expected div to have style 'position:relative;' in file {file}, found {list(content_divs)[1].attrs}")
    summary = list(content_divs)[1].find_all('div', class_='intv-summary', recursive=False)
    if len(summary) != 1:
        raise ValueError(f"Expected exactly one div.intv-summary in file {file}, found {len(summary)}")

    summary_ch = list(summary)[0].children
    field_list = [ SummaryField(name="entries", pyName="entryCount", required=True), SummaryField(name="date", required=False),
        SummaryField(name="type", pyName="entryType", required=False, plainString=True), SummaryField(name="location", required=False, plainString=True),
        SummaryField(name="bookstore", required=False, plainString=True), SummaryField(name="tourcon", required=False, plainString=True),
        SummaryField(name="reporter", required=False, plainString=True), SummaryField(name="links", required=False) ]
    field_set = {}
    for field in field_list:
        field_set[field.name] = field
    fields = {}
    mode = None
    mode_h4 = None
    key = None
    extra_paragraphs = []
    for child in summary_ch:
        if child.name == 'h4':
            if not child.string:
                raise ValueError(f"Unexpected empty h4 in file {file}: {summary}")
            mode = child.string.strip().lower()
            # print(f"switching to {mode} mode")
            mode_h4 = child
            key = mode_h4.string.strip().lower()
        elif mode == None:
            if child.name == 'h3' or (child.name is None and str(child).strip() == ''):
                continue
            raise ValueError(f"Unexpected content {child} in summary before any h4 in file {file}: {summary}")
        elif mode == "links":
            # print(f"links child: {str(child)}")
            if not key in fields.keys():
                fields[key] = []
            if child.name == None:
                continue
            elif child.name == 'p':
                fields[key].append(child)
            else:
                raise ValueError(f"Unexpected content {child.name} in links section in file {file}: {summary}")
        else:
            if child.name == 'p':
                # print(f"key: {key}, child: {child}")
                if key in field_set.keys():
                    if key in fields.keys():
                        extra_paragraphs.append(child)
                    c = len(list(child.children))
                    if c == 0:
                        continue
                    if c != 1:
                        raise ValueError(f"Non-1 children {key} paragraph found in file {file}: {summary}")
                    # print(f"key {key} -> {child}")
                    fields[key] = list(child.children)[0].string
            elif child.name is None and str(child).strip() == '':
                continue
            else:
                raise ValueError(f"Unexpected content {child.name} in summary in file {file}: {summary}")
    for par in extra_paragraphs:
        # print(f"{result.id} {file}: {par} {summary}")
        parchildren = list(par.children)
        if par.name == 'p' and len(parchildren) == 1 and parchildren[0].name == 'a':
            if 'links' not in fields.keys():
                fields['links'] = []
            fields['links'].append(par)
        else:
            raise ValueError(f"Extra summary paragraphs found in file {file}: {extra_paragraphs} {summary}")
    for field in field_list:
        if field.name not in fields.keys():
            if field.required:
                raise ValueError(f"Required field {field.name} not found in file {file}: {summary}")
            continue
    for k, v in fields.items():
        field = field_set[k]
        if field.plainString:
            # print(f"field {v} {result.id}")
            result.__dict__[field.pyName] = v.string.strip()
        else:
            result.__dict__[field.pyName] = v
    result.entryCount = int(result.entryCount.string.strip())
    date = result.date
    result.date = None
    if date and date.string:
        date = re.sub(r'(\d+)[a-z]{2}, ', '\\1, ', date.string.strip()) # Remove 1st, 2nd, 3rd, 4th, etc.
        for datef in {'%b %d, %Y', '%b, %Y', '%Y'}:
            try:
                result.date = datetime.strptime(date, datef)
                break
            except ValueError as ve:
                continue
        if not result.date:
            raise ValueError(f"Date format not recognized in file {file}: {date}")
    # print(f"{result.id}")
    if result.links:
        links = []
        for link in result.links:
            # print(f"name: {link.name}")
            if link.name == 'p':
                for a in link.children:
                    if a.name == 'a':
                        # if not a.string:
                        #     raise ValueError(f"Link with no text found in file {file}: {result.links}")
                        if 'href' not in a.attrs:
                            raise ValueError(f"Link with no href found in file {file}: {result.links}")
                        links.append({"href": a.attrs['href'], "text": a.string.strip() if a.string else ""})
                    else:
                        raise ValueError(f"non-a link in file {file}: {a}")
            else:
                raise ValueError(f"non-p link in file {file}: {link}")
        result.links = links

    header_s = list(content_divs)[1].find_all('h3', recursive=False)
    if len(header_s) != 1:
        raise ValueError(f"Expected exactly one h3 in div.intv-summary in file {file}, found {len(header_s)}")
    header = list(header_s)[0]
    title = re.sub(r'^:\s*', '', str(list(header.children)[1]).strip())
    if len(title) > 0:
        result.title = title

    # print("Processed file {file}, result: {result}".format(file=file, result=result))
    return result

def main():
    html_dir = Path("./raw_html_downloads")
    print("Checking for raw HTML files in directory:", html_dir)
    
    if not html_dir.exists():
        print(f"Directory not found: {html_dir}")
        return
    
    # Iterate through all HTML files in the directory
    html_files = list(html_dir.glob("*.html")) + list(html_dir.glob("*.htm"))
    
    if not html_files:
        print(f"No HTML files found in {html_dir}")
        return
    
    print(f"Processing {len(html_files)} HTML files...", end='', flush=True)
    
    result = {}
    for html_file in html_files:
        # Find h3 elements with listintv.php links
        file_result = process_raw_html(html_file)
        result[str(file_result.id)] = file_result
        print(".", end='', flush=True)
    print("")

    with open('./processed/db.json', 'w', encoding='utf-8', errors='ignore') as d:
        print(f"Writing JSON to {d.name}")
        d.write(json.dumps(result, cls=JsonEncoder, indent=2))

    with open('./processed/mediawiki-template-tidb-switch.template', 'w', encoding='utf-8', errors='ignore') as t:
        print(f"Writing id-to-description mediawiki template code to {t.name}")
        ids = []
        for i in result.values():
            ids.append(i.id)
        ids.sort()
        missing = 0
        for id in ids:
            interview = result[str(id)]
            if not (interview.title or interview.date):
                missing = missing + 1
                continue
            title = interview.title
            if title is None:
                title = interview.id
            line = f"  | {interview.id}={title}" + (f", {{{{Date|{datetime.strftime(interview.date, '%Y %b %d')}}}}}" if interview.date else "")
            t.write(line + "\n")
        print(f"  Skipped {missing} entries with no title and no date")

if __name__ == "__main__":
    main()