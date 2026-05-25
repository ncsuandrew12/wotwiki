local m_utils = require("Module:Utils")
local m_books = require("Module:Books")
local m = {}

-- TODO:
--  - Support referencing Companion Old Tongue Dictioanry entries
--  - Support referencing specific parts of the BWB
--  - Support referencing specific parts of Origins
--  - Support Theoryland Interview Database references
--  - Support referencing a specific section of a chapter, particularly AMOL 37
function m._get_ref(frame, args, ref_dict)
    ref = nil
    if ref_dict.book then
        ref = {}
        book = m_books.book_map[string.upper(ref_dict.book)]
        text = "<i>[["..book.title.."]]</i>"
        section = nil
        if ref_dict.chapter then
            suffix = ""
            text = text..", [["..book.title.."/"
            chstr = string.lower(ref_dict.chapter)
            if chstr == "prologue" or chstr == "p" then
                section = "Prologue"
                text = text..section.."|"..section
            elseif chstr == "epilogue" or chstr == "e" then
                section = "Epilogue"
                text = text..section.."|"..section
            elseif chstr == "glossary" or chstr == "g" then
                section = "Glossary"
                text = text..section.."|"..section
                if ref_dict.entry then
                    suffix = " - [["..ref_dict.entry.."]]"
                    section = section.."-"..ref_dict.entry
                end
            else
                section = ref_dict.chapter
                text = text.."Chapter "..ref_dict.chapter.."|Chapter "..ref_dict.chapter
            end
            text = text.."]]"..suffix
        elseif ref_dict.entry then
            text = text..", [["
            if string.lower(ref_dict.entry) == "otdict" then
                text = text.."Old Tongue Dictionary]] - [["..ref_dict.word
            else
                text = text..ref_dict.entry
            end
            text = text.."]]"
            section = ref_dict.entry
        end
        ref.name = ref_dict.name or book.title..(section or "")
        ref.text = text
    else
        ref = ref_dict
    end
    return "<span class=\"references-footnote\">"..frame:extensionTag{
        name = 'ref',
        content = (ref.text or ""),
        args = { name = ref.name and ref.name or nil }
    }.."</span>"
end

return m