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
from markdownify import markdownify as md

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
    content = None
    def __str__(self):
        return f"InterviewEntry: {self.toJSON()}"
    def toJSON(self):
        return json.dumps(self.__dict__, cls=JsonEncoder)

class JsonEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, SummaryField) or isinstance(o, Interview) or isinstance(o, InterviewEntry):
            return o.__dict__
        if isinstance(o, datetime):
            return datetime.strftime(o, '%Y-%m-%d')
        return super().default(o)

def process_raw_html(file):
    """
    Find h3 elements that contain an 'a' element with href='listintv.php'
    Returns the full content of such h3 elements.
    """
    # print(f"Processing file {file}")

    match = re.search(r'^(\d+)\.html{0,1}', os.path.basename(file))
    if not match:
        raise ValueError(f"Filename does not match expected pattern: {file}")

    result = Interview()

    interview_id = int(match.group(1))
    result.id = interview_id

    # with open(file, 'r', encoding='utf-8', errors='ignore') as f:
    #     html_content = f.read()
    # soup = BeautifulSoup(html_content, 'html.parser')

    # with open("./norm_html/" + os.path.basename(file), 'w', encoding='utf-8', errors='ignore') as f:
    #     f.write(soup.prettify())

    with open("./norm_html/" + os.path.basename(file), 'r', encoding='utf-8', errors='ignore') as f:
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
    content_div = list(content_divs)[1]
    if content_divs[1].attrs["style"] != "position:relative;":
        raise ValueError(f"Expected div to have style 'position:relative;' in file {file}, found {content_div.attrs}")
    summary = content_div.find_all('div', class_='intv-summary', recursive=False)
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
                    # print(f"{key} in {fields.keys()}?")
                    if key in fields.keys():
                        extra_paragraphs.append(child)
                        continue
                    c = len(list(child.children))
                    if c == 0:
                        continue
                    if c != 1:
                        raise ValueError(f"Non-1 children {key} paragraph found in file {file}: (mode {mode}) {child}")
                    # print(f"key {key} -> {child}")
                    fields[key] = list(child.children)[0].string
            elif child.name is None and str(child).strip() == '':
                continue
            else:
                raise ValueError(f"Unexpected content {child.name} in summary in file {file}: {summary}")
    for par in extra_paragraphs:
        # print(f"{result.id} {file}: {par} {summary}")
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
                    raise ValueError(f"Unexpected summary paragraphs found in file {file}: {par} {summary}")
        else:
            raise ValueError(f"Extra summary paragraphs found in file {file}: {par} {summary}")
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
    if date and date.string and date.string.strip() != '':
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
                    elif a.name == None and (a.string == None or a.string.strip() == ''):
                        continue
                    else:
                        raise ValueError(f"non-a link in file {file}: {a}")
            elif link.name == 'a':
                # if not link.string:
                #     raise ValueError(f"Link with no text found in file {file}: {result.links}")
                if 'href' not in link.attrs:
                    raise ValueError(f"Link with no href found in file {file}: {result.links}")
                links.append({"href": link.attrs['href'], "text": link.string.strip() if link.string else ""})
            elif link.name == None and (link.string == None or link.string.strip() == ''):
                continue
            else:
                raise ValueError(f"non-ap link in file {file}: {link}")
        result.links = links

    header_s = content_div.find_all('h3', recursive=False)
    if len(header_s) != 1:
        raise ValueError(f"Expected exactly one h3 in div.intv-summary in file {file}, found {len(header_s)}")
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
        raise ValueError(f"Unexpected header structure in file {file}, {header_c}")

    entry_list_div = content_div.find_all('div', class_='intv-entry-list', recursive=False)
    if len(entry_list_div) != 1:
        raise ValueError(f"Expected exactly one div.intv-entry-list in file {file}, found {len(entry_list_div)}")
    entry_list_ul = list(entry_list_div)[0].find_all('ul', recursive=False)
    if len(entry_list_ul) != 1:
        raise ValueError(f"Expected exactly one entry list ul in file {file}, found {len(entry_list_ul)}")
    result.entries = []
    # for entry_li in entry_list_ul[0].children:
    #     if entry_li.name == 'li':
    #         print(f"1 Entry li before processing: {entry_li.name}")
    #         for entry_li_c in entry_li.children:
    #             print(f"1  Entry li before processing: {entry_li_c.name}")
    for entry_li in entry_list_ul[0].children:
        if entry_li.name == 'li':
            # print(f"2 Entry li before processing: {entry_li.name}")
            result.entries.append(InterviewEntry())
            entry_li_iter = iter(entry_li.children)
            entry_li_c = next(entry_li_iter)
            # print(f"2  Entry li before processing: {entry_li_c.name}")
            # Skip all empty text nodes
            if entry_li_c.name == None and (entry_li_c.string == None or entry_li_c.string.strip() == ''):
                # print(f"Skipping empty text node in entry li in file {file}: {entry_li_c}")
                entry_li_c = next(entry_li_iter)
                # print(f"2  Entry li before processing: {entry_li_c.name}")
            if entry_li_c.name == 'a':
                if 'href' not in entry_li_c.attrs:
                    if 'name' in entry_li_c.attrs:
                        if len(result.entries) != int(entry_li_c.attrs['name'].strip()):
                            raise ValueError(f"Entry li.a with unexpected name found in file {file}: {entry_li_c.attrs}")
                    else:
                        raise ValueError(f"Entry li.a with no href or name found in file {file}: {entry_li}")
                else:
                    raise ValueError(f"Entry li.a with href found in file {file}: {entry_li}")
            else:
                raise ValueError(f"Entry li[0] with unexpected name {entry_li_c.name} found in file {file}: {entry_li_c}")
            entry_li_c = next(entry_li_iter)
            # Skip all empty text nodes
            if entry_li_c.name == None and (entry_li_c.string == None or entry_li_c.string.strip() == ''):
                entry_li_c = next(entry_li_iter)
            # print(f"entry-num div expected: in {file}: {entry_li_c}")
            # print(f"{entry_li_c.name} {entry_li_c.attrs} {entry_li_c.attrs['class']}")
            if entry_li_c.name == 'div' and 'class' in entry_li_c.attrs and len(entry_li_c.attrs['class']) == 1 and entry_li_c.attrs['class'][0] == 'entry-num':
                entry_li_c_children = list(entry_li_c.children)
                if len(entry_li_c_children) != 3:
                    raise ValueError(f"Entry li.div<entry-num> with unexpected children found in file {file}: {entry_li}")
                if entry_li_c_children[1].name == 'p':
                    entry_li_p_children = list(entry_li_c_children[1].children)
                    if len(entry_li_p_children) != 1:
                        raise ValueError(f"Entry li.div<entry-num>.p with unexpected children found in file {file}: {entry_li}")
                    if len(result.entries) != int(entry_li_p_children[0].string.strip()):
                        raise ValueError(f"Entry li.div<entry-num>.p with unexpected number found in file {file}: {entry_li}")
                else:
                    raise ValueError(f"Entry li.div<entry-num> with no p child found in file {file}: {entry_li}")
            else:
                raise ValueError(f"Entry li[1] with unexpected name {entry_li_c.name} found in file {file}: {entry_li_c}")
            entry_li_c = next(entry_li_iter)
            # Skip all empty text nodes
            if entry_li_c.name == None and (entry_li_c.string == None or entry_li_c.string.strip() == ''):
                entry_li_c = next(entry_li_iter)
            if entry_li_c.name == 'div' and 'class' in entry_li_c.attrs and len(entry_li_c.attrs['class']) == 1 and entry_li_c.attrs['class'][0] == 'entry-data':
                result.entries[len(result.entries)-1].content = md(str(entry_li_c))
            else:
                raise ValueError(f"Entry li[2] with unexpected name {entry_li_c.name} found in file {file}: {entry_li}")
            entry_li_c = next(entry_li.children)
            if entry_li_c and entry_li_c.name == None and (entry_li_c.string == None or entry_li_c.string.strip() == ''):
                entry_li_c = next(entry_li.children)
        elif entry_li.name == None and (entry_li.string == None or entry_li.string.strip() == ''):
            continue
        else:
            raise ValueError(f"Non-li element in entry list in file {file}: {entry_li}")

    # TODO process interview db tags

    # print("Processed file {file}, result: {result}".format(file=file, result=result))
    return result

def main():
    html_dir = Path("./raw_html_downloads")
    web_root = Path("../../web/theoryland/interviews")
    basename = "theoryland interview database"
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
    
    interviews = {}
    for f in html_files:
        # Find h3 elements with listintv.php links
        interview = process_raw_html(f)
        interviews[str(interview.id)] = interview
        print(".", end='', flush=True)
    print("")

    with open(f"{web_root}/{basename}.json", 'w', encoding='utf-8', errors='ignore') as f:
        print(f"Writing JSON to {f.name}")
        f.write(json.dumps(interviews, cls=JsonEncoder, indent=2))

    # TODO Use beautifulsoup to convert our objects to HTML and compare against the (normalized) original HTML
    # as a verification of proper parsing.

    # with open('./processed/db.json', 'r', encoding='utf-8', errors='ignore') as f:
    #     print(f"Reading JSON from {f.name}")
    #     interviews = json.load(f)

    # with open('./processed/db.md', 'w', encoding='utf-8', errors='ignore') as f:
        # print(f"Writing Markdown to {f.name}")
    print(f"Writing Markdown to {web_root}/db-*.md", end='', flush=True)
    for i in range(1, len(interviews)+1):
        print(".", end='', flush=True)
        with open(f"{web_root}/db-{i}.md", 'w', encoding='utf-8', errors='ignore') as f:
            # print(f"Writing Markdown to {f.name}")
            interview = interviews[str(i)]
            f.write(f"# Interview #{interview.id}" + (f": {interview.title}" if interview.title else "") + "\n\n")
            if interview.date:
                f.write(f"- Date: {datetime.strftime(interview.date, '%Y-%m-%f')}\n\n")
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
                f.write("- Links\n\n")
                for link in interview.links:
                    f.write(f"-- [" + (link['text'] if link['text'] else link['href']) + f"]({link['href']})\n\n")
                f.write("\n")
            entry_i = 0
            for entry in interview.entries:
                entry_i += 1
                f.write(f"## Entry #{entry_i}\n\n")
                f.write(entry.content + "\n\n")
            f.write("\n---\n\n")
    print("")

    with open(f"{web_root}/index.md", 'w', encoding='utf-8', errors='ignore') as f:
        print(f"Writing id-to-description mediawiki template switch code to {f.name}")
        f.write("# [Theoryland Interview Database](https://www.theoryland.com/listintv.php)\n\n")
        f.write("## Downloads\n\n")
        f.write(f"* Full archive [JSON](./{basename}.json)\n\n")
        f.write(f"* Full archive [Markdown](./{basename}.md)\n\n")
        f.write("## Interviews\n\n")
        for i in range(1, len(interviews)+1):
            f.write(f"- [Interview #{i} - " + (f": {interviews[str(i)].title}" if interviews[str(i)].title else "") + f"](./db-{i})" + "\n")

    os.makedirs("./processed", exist_ok=True)
    with open('./processed/mediawiki-template-tidb-switch.template', 'w', encoding='utf-8', errors='ignore') as f:
        print(f"Writing id-to-description mediawiki template switch code to {f.name}")
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
        print(f"  Skipped {missing} entries with no title and no date")

if __name__ == "__main__":
    main()