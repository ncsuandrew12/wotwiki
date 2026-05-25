#!/bin/bash
set -e

cat "../wotwiki/modules/wotwiki-secret/source material/the-complete-wheel-of-time.md" | \
    sed -e 's/[“”]/"/' | sed -e 's/…/.../g' | sed -e 's/—/-/g' | sed -e 's/[*_]//' | sed -e 's/\x2019/\x27/' | \
    grep -oE "[^\.\!\?\"'-]\s([A-Z][a-z'][A-Za-z']*)(\s [A-Z]){0,1}" | \
    sed -e 's/^(.*\S)\s+$/$1/g' | sed -e "s/^\s+(\S.*)$/$1/g" | sed -e "s/^\S\s\+//g" | \
    sort -u | sed -e '/\x27s/d' > /tmp/wot_proper_nouns.txt

cat "../wotwiki/modules/wotwiki-secret/source material/the-wheel-of-time-companion.md" | \
    sed -e 's/[“”]/"/' | sed -e 's/…/.../g' | sed -e 's/—/-/g' | sed -e 's/[*_]//' | sed -e 's/\x2019/\x27/' | \
    grep -oE "\[([A-Z][a-z'][A-Za-z' ]*)\]" | sed -e "s/^\[//g" | sed -e "s/\]$//g" | \
    sed -e 's/^(.*\S)\s+$/$1/g' | sed -e "s/^\s+(\S.*)$/$1/g" | sort -u >> /tmp/wot_proper_nouns.txt

cat /tmp/wot_proper_nouns.txt | sort -u > ./wot_proper_ish_nouns.txt

ish_count=$(wc -l < ./wot_proper_ish_nouns.txt)
blacklist_count=$(wc -l < ./wot_proper_noun_blacklist.txt)

touch ./wot_proper_noun_blacklist.txt
grep -xv -f ../wotwiki/data/wot_proper_noun_blacklist.txt ./wot_proper_ish_nouns.txt > ./wot_proper_nouns.txt

cat ./wot_proper_nouns.txt
count=$(wc -l < ./wot_proper_nouns.txt)
echo ""
echo "${ish_count} LESS ${blacklist_count} = ${count}"
