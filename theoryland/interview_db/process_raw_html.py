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

class Interview:
    id = None
    title = None
    date = None
    def __str__(self):
        return f"Interview: {self.toJSON()}"
    def toJSON(self):
        return json.dumps(self.__dict__, cls=JsonEncoder)

class JsonEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Interview):
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

    with open(file, 'r', encoding='utf-8', errors='ignore') as f:
        html_content = f.read()
    soup = BeautifulSoup(html_content, 'html.parser')
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
    header_s = list(content_divs)[1].find_all('h3', recursive=False)
    if len(header_s) != 1:
        raise ValueError(f"Expected exactly one h3 in div.intv-summary in file {file}, found {len(header_s)}")
    header = list(header_s)[0]

    result.id = interview_id

    summary_ch = list(summary)[0].children
    last_2_child = None
    last_child = None
    date_str = None
    for child in summary_ch:
        # if last_2_child:
        #     print(f"child.name: {child.name}, lcn: {last_2_child.name}, s: {last_2_child.string.strip()}, child: {child} last_child: {last_2_child}")
        # else:
        #     print(f"child.name: {child.name}, child: {child} last_child: {last_2_child}")
        if child.name == 'p' and last_2_child and last_2_child.name == 'h4' and last_2_child.string and last_2_child.string.strip() == 'Date':
            if date_str:
                raise ValueError(f"Multiple date paragraphs found in file {file}: {summary}")
            if child.string:
                date_str = child.string.strip()
            break
        last_2_child = last_child
        last_child = child
    if date_str:
        date_str = re.sub(r'(\d+)[a-z]{2}, ', '\\1, ', date_str) # Remove 1st, 2nd, 3rd, 4th, etc.
        for datef in {'%b %d, %Y', '%b, %Y', '%Y'}:
            try:
                result.date = datetime.strptime(date_str, datef)
                break
            except ValueError as ve:
                continue
        if not result.date:
            raise ValueError(f"Date format not recognized in file {file}: {datestr}")
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