#!/usr/bin/env python3

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

logger = logging.getLogger("s2j")
logging.basicConfig(
    filename='s2j.log',
    level=logging.INFO,
    format='%(levelname)s - %(filename)s:%(lineno)3d - %(message)s'
)
logger.addHandler(logging.StreamHandler(sys.stdout))

class Site:
    name = None
    wot_centric = None
    show = None
    subsites = None
    sites_count = 1
    defunct = False

    def __init__(self):
        self.name = None
        self.wot_centric = None
        self.show = None
        self.subsites = []
        self.sites_count = 1
        self.defunct = False

    def __str__(self):
        return "Site: " + self.toJSON()
    
    def jsonDict(self):
        d = self.__dict__.copy()
        d.pop("sites_count")
        for key in [ "wot_centric", "show" ]:
            if (d[key] == None) or (d[key] == ""):
                d.pop(key)
        if not self.defunct:
            d.pop("defunct")
        return d

    def toJSON(self):
        return json.dumps(self.jsonDict(), cls=JsonEncoder)

class Subsite:
    site_url = None
    site_text = None
    site_type = None
    audience = None
    notes = None
    
    def __init__(self):
        self.site_url = None
        self.site_text = None
        self.site_type = None
        self.audience = None
        self.notes = None
    
    def __str__(self):
        return "Subsite: " + self.toJSON()
    
    def jsonDict(self):
        d = self.__dict__.copy()
        for key in [ "site_text", "audience", "notes" ]:
            if (d[key] == None) or (d[key] == "") or (len(d[key]) == 0):
                d.pop(key)
        return d
        
    def toJSON(self):
        return json.dumps(self.jsonDict(), cls=JsonEncoder)

class JsonEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Site) or isinstance(o, Subsite):
            return o.jsonDict()
        if isinstance(o, datetime):
            return datetime.strftime(o, '%Y-%m-%d')
        return super().default(o)

def main():
    input_file = Path("./wotsites.wiki")
    output_file = Path("./wotsites.json")
    logger.setLevel(logging.INFO)

    sites = []
    with (open(input_file, 'r', encoding='utf-8')) as infile:
        state = "new"
        site_rowcount = 0
        subsite_rowcount = 0
        site_attrs = [ "name", "wot_centric", "show", "site_url", "site_type", "audience", "notes" ]
        for line in infile:
            line = line.strip()
            logger.info(f"Processing line (state={state}): {line}" + (f":\n                                                                                                                                            {sites[-1]}" if len(sites) > 0 else ""))
            if state == "new":
                if line.startswith("{|"):
                    state = "table_started"
                    continue
                raise RuntimeError(f"Unexpected line while looking for table start in state {state}: {line}")
            elif state == "table_started":
                if line == "|+":
                    state = "table_header"
                    continue
                raise RuntimeError(f"Unexpected line while looking for table header in state {state}: {line}")
            elif state == "table_header":
                if line.startswith("!"):
                    continue
                elif line == "|-":
                    state = "site"
                    sites.append(Site())
                    site_rowcount = 0
                    subsite_rowcount = 0
                    continue
                raise RuntimeError(f"Unexpected line while looking for table header row in state {state}: {line}")
            elif state == "site":
                if line == "|-" and site_rowcount == 7:
                    sites.append(Site())
                    site_rowcount = 0
                    subsite_rowcount = 0
                    continue
                elif line.startswith("|") and site_rowcount == 3:
                    state = "subsite"
                    if (line == "|-"):
                        sites[-1].subsites.append(Subsite())
                        continue
                elif line == "|-":
                    raise RuntimeError(f"Unexpected entry separator while looking for site row separator in state {state}: {line}")
                if not line.startswith("|"):
                    raise RuntimeError(f"Unexpected line while looking for site row in state {state}: {line}")
                else:
                    if site_rowcount == 2:
                        sites[-1].subsites.append(Subsite())
                    match = re.search(r'^\| rowspan=(\d+) +\|(.*)$', line)
                    val = None
                    if match:
                        if site_attrs[site_rowcount] == "name":
                            logger.info(f"Site found: {match.group(2).strip()}")
                            sites[-1].sites_count = int(match.group(1))
                        val = match.group(2).strip()
                    else:
                        val = line[1:].strip()
                    if site_rowcount <= 2:
                        logger.info(f"site field index {site_rowcount} + {subsite_rowcount} = {site_rowcount + subsite_rowcount}")
                        sites[-1].__dict__[site_attrs[site_rowcount + subsite_rowcount]] = val
                    else:
                        if len(sites[-1].subsites) == 0:
                            sites[-1].subsites.append(Subsite())
                        logger.info(f"site-subsite field index {site_rowcount} + {subsite_rowcount} = {site_rowcount + subsite_rowcount}")
                        sites[-1].subsites[-1].__dict__[site_attrs[site_rowcount + subsite_rowcount]] = val
                if site_rowcount == 3:
                    subsite_rowcount += 1
                else:
                    site_rowcount += 1
            elif state == "subsite":
                if line == "|-":
                    if subsite_rowcount == 4:
                        logger.info(f"Completed subsite for site {sites[-1].name}: {len(sites[-1].subsites)} ? {sites[-1].sites_count}: {sites[-1].subsites[-1]}")
                        if len(sites[-1].subsites) > sites[-1].sites_count:
                            raise RuntimeError(f"Subsite count mismatch for site {sites[-1].name}: expected {sites[-1].sites_count}, found {len(sites[-1].subsites)}: {line}")
                        elif len(sites[-1].subsites) == sites[-1].sites_count:
                            state = "site"
                            sites.append(Site())
                            site_rowcount = 0
                            subsite_rowcount = 0
                        elif len(sites[-1].subsites) <= sites[-1].sites_count:
                            sites[-1].subsites.append(Subsite())
                        subsite_rowcount = 0
                        continue
                    continue
                if not line.startswith("|"):
                    if subsite_rowcount < 4:
                        raise RuntimeError(f"Unexpected line while looking for subsite row in state {state}: {line}")
                    if len(line.strip()) > 0:
                        if sites[-1].subsites[-1].notes == None:
                            sites[-1].subsites[-1].notes = []
                        sites[-1].subsites[-1].notes.append(line.strip())
                else:
                    logger.info(f"subsite field index {site_rowcount} + {subsite_rowcount} = {site_rowcount + subsite_rowcount}")
                    attr = site_attrs[min(6, site_rowcount + subsite_rowcount)]
                    if len(line[1:].strip()) > 0:
                        if attr == "notes":
                            if sites[-1].subsites[-1].notes == None:
                                sites[-1].subsites[-1].notes = []
                            sites[-1].subsites[-1].notes.append(line[1:].strip())
                        else:
                            sites[-1].subsites[-1].__dict__[attr] = line[1:].strip()
                    subsite_rowcount += 1
            else:
                raise RuntimeError(f"Unknown state {state} while processing line: {line}")
    defunct = False
    for site in sites:
        for key in [ "name", "subsites" ]:
            if (site.__dict__[key] == None) or (site.__dict__[key] == ""):
                raise RuntimeError(f"Required key {key} missing in site {site.name}")
        for subsite in site.subsites:
            for key in [ "site_url", "site_type" ]:
                if (subsite.__dict__[key] == None) or (subsite.__dict__[key] == ""):
                    raise RuntimeError(f"Required key {key} missing in site {site.name}")
            if subsite.site_url == "":
                subsite.site_url = None
            if subsite.site_url != None:
                match = re.search(r'^\{\{Link *\|url=([^ ]+) *\|text=([^}]+)\}\}$', subsite.site_url)
                if match:
                    subsite.site_text = match.group(2).strip()
                    subsite.site_url = match.group(1).strip()
                if not match:
                    match = re.search(r'^\{\{Link *\|url=([^ ]+)\}\}$', subsite.site_url)
                    if match:
                        subsite.site_text = None
                        subsite.site_url = match.group(1).strip()
                if not match:
                    match = re.search(r'^\{\{Subreddit *\|([^ ]+)\}\}$', subsite.site_url)
                    if match:
                        subsite.site_text = None
                        subsite.site_url = match.group(1).strip()
                if not match:
                    raise RuntimeError(f"Site URL not in expected format for site {site.name}: {subsite.site_url}")
            if subsite.audience == "":
                subsite.audience = None
            if subsite.audience != None:
                match = re.search(r'^\{\{RoughPop *\|(\d+)\}\}$', subsite.audience)
                if not match:
                    raise RuntimeError(f"Site audience not in expected format for site {site.name}: {subsite.audience}")
                else:
                    subsite.audience = match.group(1).strip()
            elif site.name.startswith("A Compendium"):
                defunct = True
            site.defunct = defunct
    new_sites = []
    for sitename in ["WoT Wiki", "Narg the Trolloc", "Wetlander Humor", "c/WoT", "WoT Compendium", "Theoryland", "Wheel of Timelines", "Encyclopaedia WoT", "The Compendium of ''Wheel of Time'' Characters",
                     "WoT Notes", "13th Depository", "The Old Tongue Dictionary", "Tar Valon", "The Band of the Red Hand", "Defenders of the Dragon",
                     "Wheel of Time Quiz", "Dragonmount", "17th Shard", "JordanCon"]:
        logger.info(f"Preferred site: {sitename}")
        sc = len(sites)
        for site in sites:
            logger.info(f"Comparing preferred site: {sitename}: {site.name}")
            if site.name == sitename:
                logger.info(f"Found preferred site: {site.name}")
                new_sites.append(site)
                sites.remove(site)
                break
        if len(sites) != sc - 1:
            raise RuntimeError(f"Site {sitename} not found for initial reordering")
    ordered_sitenames = []
    for site in sites:
        if site.name not in ordered_sitenames:
            ordered_sitenames.append(site.name)
    ordered_sitenames.sort()
    for sitename in ordered_sitenames:
        logger.info(f"Other site: {sitename}")
        transfer_sites = []
        for site in sites:
            logger.info(f"Comparing other site: {sitename}: {site.name}")
            if site.name == sitename:
                logger.info(f"Found other site: {site.name}: {site}")
                transfer_sites.append(site)
        for site in transfer_sites:
            new_sites.append(site)
            sites.remove(site)
        if len(sites) >= sc:
            raise RuntimeError(f"Site {sitename} not found for reordering")
    if len(sites) > 0:
        raise RuntimeError(f"Some sites not reordered: {len(sites)} remaining: {json.dumps(sites, cls=JsonEncoder)}")
    sites = new_sites
    with open(output_file, 'w', encoding='utf-8') as f:
        logger.info(f"Writing JSON to {f.name}")
        f.write(json.dumps(sites, cls=JsonEncoder, indent=2))

if __name__ == "__main__":
    main()