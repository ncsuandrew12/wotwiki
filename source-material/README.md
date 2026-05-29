# Purpose

The purpose of this directory is to be, together with the `modules/wotwiki-secret/source material` directory, a repository of as much *Wheel of Time* source material as possible. If you have access, see [the README in that directory](../modules/wotwiki-secret/source%20material/README.md) for more information.

The primary goal is to have at least one copy of every piece of source material. To that end, EPUBs and PDFs are preferred, but in general any format is acceptable, particularly if it is the format in which the material was published.

The secondary goal is for someone to be able to run a plain text search on the contents of this directory and find every relevant result in WoT source material. To that end, we want to have copies of every piece of material in a plaintext format. Markdown is preferred, but wikitext or basic raw text are also acceptable.

The tertiary goal is to provide source material in machine-consumable formats to facilitate the creation of programs and scripts which do useful or interesting things, such as data analysis, codification and indexing, annotating, etc. To that end, it is also desirable to have all material in structured formats. JSON is preferred, but other formats like XML or YAML are also acceptable.

# Duplicates

We generally try to avoid multiple copies of the same material (for example, we have files for the main series text from *The Complete Wheel of Time* ebook, but not from the individual ebooks of *The Eye of the World* or *The Great Hunt*), but there are times when it makes sense to have duplicate material. For example, different formats (PDF, EPUB, JSON, Markdown, wikitext, etc) or larger/smaller compilations (for example, having the entire series in a single file and having a directory of per-book or per-chapter files).

# Deviations From Source

Files should generally be as close to the represented publication as possible. Typos from original text, such as spelling errors or mistaken Unicode characters, should be preserved. However, if they were fixed in later editions, then it is appropriate to fix them here, provided that it is clear what the file is intended to represent. For example, a file titled 'the-eye-of-the-world.md' would by any reasonable person be expected to represent the "official" version of *The Eye of the World* and may be updated to reflect any changes in recent editions of the book, but a file titled 'the-eye-of-the-world-1990.md' or 'the-eye-of-the-world-first-ed.json' would be expected to represent the original 1990 first edition and should not be updated to reflect changes in later editions.

Files meant for human use, such as Markdown files, may be edited to improve readability, such as by replacing esoteric Unicode characters. However, files meant for machine use, such as JSON files, should not be edited in this way.

# Specific Files

- [Beasts of the Wheel of Time.wiki](./Beasts%20of%20the%20Wheel%20of%20Time.wiki) is meant to be an exact duplicate of the wikitext of the [wiki page](https://wot.fandom.com/wiki/Beasts_of_the_Wheel_of_Time)'s *[Article text](https://wot.fandom.com/wiki/Beasts_of_the_Wheel_of_Time#Article_text)* section. If there are differences, then one or the other likely needs updating. In general, the wiki page is likely to be the more up-to-date version.