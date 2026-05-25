local m_utils = require("Module:Utils")
local m_books = require("Module:Books")
local m = {}

-- TODO:
--  - Support referencing Companion Old Tongue Dictioanry entries
--  - Support referencing specific parts of the BWB
--  - Support referencing specific parts of Origins
--  - Support Theoryland Interview Database references
--  - Support referencing a specific section of a chapter, particularly AMOL 37
function m._get_ref(frame, args, refp)
    local ref = nil
    if type(refp) == "table" then
        if refp.book then
            ref = {}
            local book = m_books.book_map[string.upper(refp.book)]
            if book == nil then
                return m_utils._error(frame, "Invalid book reference: "..refp.book)
            end
            local text = "<i>[["..book.title.."]]</i>"
            local section = nil
            if refp.chapter then
                local suffix = ""
                text = text..", [["..book.title.."/"
                local chstr = string.lower(refp.chapter)
                if chstr == "prologue" or chstr == "p" then
                    section = "Prologue"
                    text = text..section.."|"..section
                elseif chstr == "epilogue" or chstr == "e" then
                    section = "Epilogue"
                    text = text..section.."|"..section
                elseif chstr == "glossary" or chstr == "g" then
                    section = "Glossary"
                    text = text..section.."|"..section
                    if refp.entry then
                        suffix = " - [["..refp.entry.."]]"
                        section = section.."-"..refp.entry
                    end
                else
                    section = refp.chapter
                    text = text.."Chapter "..refp.chapter.."|Chapter "..refp.chapter
                end
                text = text.."]]"..suffix
            elseif refp.entry then
                text = text..", [["
                if string.lower(refp.entry) == "otdict" then
                    text = text.."Old Tongue Dictionary]] - <i>[["..refp.word.."]]</i>"
                else
                    text = text..refp.entry.."]]"
                end
                section = refp.entry
            end
            ref.name = refp.name or book.title..(section or "")
            ref.text = text
        else
            ref = refp
        end
    else
        ref = { text = tostring(refp) }
    end
    return "<span class=\"references-footnote\">"..frame:extensionTag{
        name = 'ref',
        content = (ref.text or ""),
        args = { name = ref.name and ref.name or nil }
    }.."</span>"
end

return m