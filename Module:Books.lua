local m_utils = require('Module:Utils')
local m_data = mw.loadJsonData('Module:Books/Data/data.json')

local m = {}

m.books = {}
m.book_map = {}
m.wot_series = {}

for book_index, book_ro in ipairs(m_data) do
    local book = { title=book_ro["title"], abbrev=book_ro["abbrev"], number=book_ro["number"], wot_series=book_ro["wot_series"], template=book_ro["template"], templates=book_ro["templates"], chapters_ro=book_ro["chapters"] }
    table.insert(m.books, book)
    if book.title == nil then error("Book "..book_index.." has no title.") end
    m.book_map[string.upper(book.title)] = book
    if book.abbrev ~= nil then m.book_map[string.upper(book.abbrev)] = book end
    book.index = book_index
    -- if book["wot_main_series"] ~= nil then
    --     local val = book["wot_main_series"]
    --     book["wot_main_series"] = nil
    --     book.wot_main_series = val
    -- end
    if book.wot_series == true then
        if book.abbrev == nil then error("Book "..book.title.." in WoT series has no abbreviation.") end
        table.insert(m.wot_series, book)
        if book.index ~= 1 then
            book.previous = m.books[book.index - 1]
            book.previous.next = book
        end
        if book.number == nil then error("Book "..book.title.." in WoT series has no number.") end
        if book.template == nil and book.templates == nil then
            book.templates = { tostring(book.number), string.lower(book.abbrev) }
        end
    end
    if book.template ~= nil then
        if book.templates ~= nil then error("Book "..book.title.." has both template and templates fields.") end
        book.templates = { book.template }
        book.template = nil
    end
    if book.templates ~= nil then
        for _, template in ipairs(book.templates) do
            if m.book_map[template] ~= nil then error("Duplicate book template "..template.." for books "..m.book_map[template].title.." and "..book.title..".") end
            m.book_map[template] = book
        end
    end
    if book.chapters_ro ~= nil then
        book.chapters = {}
        book.chapters_map = {}
        for chapter_index, chapter_ro in ipairs(book.chapters_ro) do
            local chapter = { index = chapter_index, title = chapter_ro["title"], number=chapter_ro["number"], book_subpage = chapter_ro["book_subpage"], type = chapter_ro["type"] }
            table.insert(book.chapters, chapter)
            book.chapters_map[tostring(chapter.index)] = chapter
            book.chapters_map[chapter.index] = chapter
            if chapter.type == nil then
                chapter.type = "chapter"
            end
            if chapter.title == nil then
                if chapter.type == "chapter" then
                    chapter.title = tostring(chapter.index)
                elseif chapter.type == "prologue" then
                    chapter.title = "Prologue"
                elseif chapter.type == "epilogue" then
                    chapter.title = "Epilogue"
                end
            else
                book.chapters_map[chapter.title] = chapter
            end
            if chapter.index ~= 1 then
                chapter.previous = book.chapters[chapter.index - 1]
                chapter.previous.next = chapter
            end
            if chapter.book_subpage == nil then
                if chapter.type == "chapter" then
                    chapter.book_subpage = "Chapter "..tostring(chapter.number)
                    book.chapters_map[chapter.number] = chapter.index
                    book.chapters_map[tostring(chapter.number)] = chapter.index
                elseif chapter.type == "prologue" or chapter.type == "epilogue" then
                    chapter.book_subpage = string.gsub(chapter.type, "^%l", string.upper)
                else
                    chapter.book_subpage = string.gsub(chapter.title, "^%l", string.upper)
                end
            end
            if book.chapters_map[chapter.book_subpage] == nil then book.chapters_map[chapter.book_subpage] = chapter.index end
        end
        book.chapters_ro = nil
    end
end

function m._chapter_nav(frame, args)
    local str = "{| style=\"float: right; font-size:80%; width: 25%; max-width: 215px; border:1px solid #aaaaaa; border-top:"
    str = str..(args["header"] ~= nil and (string.len(args["header"]) > 0 and "0" or "1") or "1").."px; font-family: Verdana, sans-serif; margin: 2.8em 0 0 3.2em; padding: 1em 1em 1.5em 1em; background: rgb(220 220 220 / 30%);\"\n"
    str = str.."|-\n"
    str = str.."! colspan=\"2\" style=\"text-align: center;\" | Book Index\n"
    str = str.."|-\n"
    str = str.."| colspan=\"2\" style=\"text-align: center; font-size:70%;\" |\n"
    for book_i, book in ipairs(m.wot_series) do
        str = str.."[["..book.title.."|"..m_utils.int_to_roman_numeral[book.number].."]]"
        if book.number == 7 then -- Approximately halfway in terms of character width after conversion to roman numerals
            str = str.."<br />"
        end
        str = str.."\n"
    end
    str = str.."|-\n"
    str = str.."! colspan=\"2\" style=\"text-align: left; padding-top: 20px;\" |Chapters\n"
    str = str.."|-\n"
    str = str.."|"
    local book_key = args["book"]
    local book = m.book_map[book_key]
    if book == nil then
        book_key = string.upper(string.gsub(string.gsub(args["book"], "_", " "), "&#39;", "'"))
        book = m.book_map[book_key]
    end
    if book == nil then error("Error: No such book: "..args["book"].." -> "..book_key) end
    local chapter_mode = "intro"
    local first_intro = true
    local is_intro = false
    for _, chapter in ipairs(book.chapters) do
        local link = "[["..book.title.."/"..chapter.book_subpage.."|"..chapter.title.."]]"
        if chapter.type == "chapter" then
            if chapter_mode == "intro" then
                chapter_mode = "chapter"
                if is_intro then str = str.."\n" end
                str = str.."<table cellspacing=\"0\" cellpadding=\"0\" style=\"width: 100%; background-color: transparent; border: 0; line-height: normal;\">\n"
            elseif chapter_mode ~= "chapter" then
                error("Invalid chapter order in book "..book.title..", chapter "..chapter.index..".")
            end
            str = str.."<tr style=\"vertical-align: top;\">\n"
            str = str.."  <td style=\"text-align: right; padding-right: 0.5em;\">"..chapter.number.."</td>\n"
            str = str.."  <td style=\"text-align: left; padding-bottom: 2px;\">"..link.."</td>\n"
            str = str.."</tr>\n"
        else
            if chapter_mode == "chapter" then
                chapter_mode = "outro"
                str = str.."</table>\n"
            end
            if chapter_mode == "intro" then
                is_intro = true
                if first_intro then
                    first_intro = false
                else
                    str = str.." - "
                end
            end
            str = str..link
            if chapter_mode == "outro" then
                str = str.."\n"
            end
        end
    end
    if chapter_mode == "chapter" then
        str = str.."</table>\n"
    end
    str = str.."|-\n"
    str = str.."|}"
    return str
end

function m.chapter_nav(frame)
    return m._chapter_nav(frame, m_utils.get_merged_args(frame))
end

return m