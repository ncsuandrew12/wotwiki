local m_utils = require('Module:Utils')
-- TODO Update database code down below not to modify anything from Database,
-- then switch to loadData (or loadJsonData?) here.
-- TODO break functions that don't need DB into separate module
local m_quote_db = mw.loadData('Module:Wotq/Data/Cache')
local m_quote = require('Module:Quote')

local m = {}

-- TODO:
--   - Add the ability to search WoT quotes by book/chapter
--   - Add support for some basic boolean searching by filter
--   - Scan quote text for certain keywords and add them as tags automatically
--   - Create a new CSS class for in-quote links
--     - Formatted like regular text (in color, etc)?
--   - Add a field to control whether quote marks are automatically added to
--     a quote.
--   - Add intros to the book reference templates/code in addition to prologues
--     and epilogues. Look for ", Intro" in source refs and replace with
--     appropriate usage.
--   - Move styling into CSS.

function m._dealias_tag(frame, name)
    local name_lc = string.lower(name)
    if not m_quote_db.aliases[name_lc] then return nil end
    return m_quote_db.aliases[name_lc]
end

function m._render_wot_quote_search(frame, args)
	local quotes = m._search_wot_quotes(frame, args)
	if not quotes or #quotes == 0 then
		error("No quotes found! Check the parameters or consider [[Help:Style guide/Quotations#Updating the quote database|adding a quote to the database]].")
	end
	args = m_utils._map_union(args, { debug = false })
	args.quotes = quotes
    return m_quote._render_quotes( frame, args)
end

function m._random_wot_quote(frame, args)
	local quotes = m._search_wot_quotes(frame, args)
	if not quotes or #quotes == 0 then
		error("No quotes found! Check the parameters or consider [[Help:Style guide/Quotations#Updating the quote database|adding a quote to the database]].")
	end
	args = m_utils._map_union(args, { debug = false })
	args.quotes = { m_utils._select_random_entry(frame, args, quotes) }
    return m_quote._render_quotes( frame, args)
end

function m._search_wot_quotes(frame, args)
    local tags_str = nil
    for key, value in pairs(args) do
        if key == "tags" then
            tags_str = value
            mw.log("Parsed tags: "..tags_str)
        else
            mw.log("Unknown wot quote search field: "..key)
        end
    end
    local tags = nil
    if tags_str then
        for tag in string.gmatch(tags_str, "[^\r\n]+") do
            tag = mw.text.trim(tag)
            if tag and string.len(tag) > 0 then
                tags = m_utils._table_insert_or_create(tags, tag)
            end
        end
    end
    mw.log("Searching for WoT quotes: "..m_utils._serialize(tags, "tags"))

    local quotes = {}
    if (tags == nil) then
        quotes = m_quote_db.quotes
    else
        local plus_tags = nil
        local minus_tags = nil
        local minus_tags_plain = nil
        for _, tag_name in ipairs(tags) do
            local tag_name_lc = mw.text.trim(string.lower(tag_name))
            if string.match(tag_name_lc, "^%!") then
                -- minus_tags = m_utils._table_insert_or_create(minus_tags, m._dealias_tag(frame, mw.text.trim(string.sub(tag_name_lc, 2))))
                local t = m._dealias_tag(frame, tag_name_lc)
                if t then
                    minus_tags = m_utils._table_insert_or_create(minus_tags, t)
                else
                    minus_tags_plain = m_utils._table_insert_or_create(minus_tags_plain, { name = tag_name_lc, exact = false })
                end
            else
                local tag = m._dealias_tag(frame, tag_name_lc)
                if tag then plus_tags = m_utils._table_insert_or_create(plus_tags, tag) end
                if tag_name_lc ~= "all" then
                    local t = m._dealias_tag(frame, "!"..tag_name_lc)
                    if t then
                        minus_tags = m_utils._table_insert_or_create(minus_tags, t)
                    else
                        minus_tags_plain = m_utils._table_insert_or_create(minus_tags_plain, { name = "!"..tag_name_lc, exact = true })
                    end
                end
            end
        end
        mw.log("Searching for WoT quotes: "..m_utils._serialize(plus_tags, "plus_tags").."; "..m_utils._serialize(minus_tags, "minus_tags"))
        -- For all tags provided in the arguments
        if plus_tags then
            -- TODO use indeces to speed up the removal filtering.
            for _, plus_tag in ipairs(plus_tags) do
                mw.log("Checking plus_tag: "..plus_tag.short)
                for _, q in ipairs(plus_tag.quotes) do
                    mw.log("Adding quote to search results (plus_tag: "..plus_tag.short.."): "..m_utils._serialize(q, "q"))
                    table.insert(quotes, q)
                end
                if plus_tag.quotes then
                    for _, db_quote in ipairs(plus_tag.quotes) do
                        mw.log("Checking quote: "..m_utils._serialize(db_quote, "db_quote"))
                        local add = true
                        if add then
                            for _, added_quote in ipairs(quotes) do
                                if added_quote.index == db_quote.index then
                                    add = false
                                    break
                                end
                            end
                        end
                        if add then
                            mw.log("Adding quote to search results (plus_tag: "..plus_tag.."): "..m_utils._serialize(db_quote, "db_quote"))
                            table.insert(quotes, db_quote)
                        end
                    end
                end
            end
        end
        if minus_tags then
            for _, minus_tag in ipairs(minus_tags) do
                mw.log(string.format("Checking minus_tag: %s", minus_tag.short))
                if minus_tag.quotes then
                    for _, q in ipairs(minus_tag.quotes) do
                        local remove_count = 0
                        for i, quote in ipairs(quotes) do
                            if quote.index == q.index then
                                mw.log(string.format("Removing quote from search results (minus_tag: %s): %s",
                                    minus_tag.short, m_utils._serialize(q, "q")))
                                table.remove(quotes, i - remove_count)
                                remove_count = remove_count + 1
                                break
                            end
                        end
                    end
                end
            end
        end
        if minus_tags_plain then
            local remove_count = 0
            for db_quote_i, db_quote in ipairs(quotes) do
                if db_quote.tags then
                    for _, minus_tag in ipairs(minus_tags_plain) do
                        for _, db_tag_i in ipairs(db_quote.tags) do
                            local db_tag = m_quote_db.tags_array[db_tag_i]
                            mw.log(string.format("Comparing minus_tag and db_tag: %s, %s", minus_tag.name, db_tag.short))
                            local ts_lc = string.lower(db_tag.short)
                            if minus_tag.name == ts_lc or (not minus_tag.exact and string.match(minus_tag.name, "^%!") and minus_tag.name == "!"..ts_lc) then
                                mw.log(string.format(
                                    "Removing quote from search results (minus_tag: %s): %s",
                                    minus_tag.name, m_utils._serialize(db_quote, "db_quote")))
                                table.remove(quotes, db_quote_i - remove_count)
                                remove_count = remove_count + 1
                                break
                            end
                        end
                    end
                end
            end
        end
    end
    local new_quotes = {}
    for _, q in ipairs(quotes) do
        local quote = {
            index = q.index, quote = q.quote, early_refs = q.early_refs, speakers = nil,
            addressees = nil, pseudosource = nil, description = q.description,
            description_extra = q.description_extra, topic = q.topic, book_refs = q.book_refs,
            other_refs = q.other_refs, tags = {}
        }
        if type(quote.quote) == "table" then
            local lines = quote.quote
            quote.quote = {}
            for _, v in ipairs(lines) do
                table.insert(quote.quote, {
                    participant = m._clone_tag(m_quote_db.tags_array[v.participant]),
                    text = v.text, quote_marks = v.quote_marks
                })
            end
        end
        for _, key in ipairs({"speakers", "addressees", "pseudosource"}) do
            local v = q[key]
            if v then
                if type(v) == "table" then
                    local tags = {}
                    for _, ti in ipairs(v) do
                        table.insert(tags, m._clone_tag(m_quote_db.tags_array[ti]))
                    end
                    quote[key] = tags
                else
                    quote[key] = m._clone_tag(m_quote_db.tags_array[v])
                end
            end
        end
        table.insert(new_quotes, quote)
        if quote.tags then
            local tags = q.tags
            for _, ti in ipairs(tags) do
                local t = m_quote_db.tags_array[ti]
                local tag = m._clone_tag(t)
                table.insert(quote.tags, tag)
            end
        end
    end
    return new_quotes
end

function m._clone_tag(t)
    return { index = t.index, page = t.page, name = t.name, short = t.short, aliases = t.aliases, quotes = nil }
end

function m._wot_stats(frame)
    local stats = {}
    local names = {}
    local implicit_cnt = 0
    local implicit_aliases = {}
    local implicit_quotes = {}
    for _, tag in pairs(m_quote_db.tags) do
        local count = 0
        -- if tag.implicit then
        --     if tag.quotes then
        --         for _, q in ipairs(tag.quotes) do
        --             local counts = true
        --             for _, qi in ipairs(implicit_quotes) do
        --                 if q.index == qi then
        --                     counts = false
        --                     break
        --                 end
        --             end
        --             if counts then
        --                 implicit_cnt = implicit_cnt + 1
        --                 table.insert(implicit_quotes, q.index)
        --             end
        --         end
        --     end
        --     for _, alias in ipairs(tag.aliases) do
        --         local add = true
        --         for _, ia in ipairs(implicit_aliases) do
        --             if alias == ia then
        --                 add = false
        --                 break
        --             end
        --         end
        --         if add then table.insert(implicit_aliases, alias) end
        --     end
        -- else
            if tag.quotes then
                for _, _ in ipairs(tag.quotes) do
                    count = count + 1
                end
            end
            stats[tag.name] = { tag = tag, count = count }
            table.insert(names, tag.name)
        -- end
    end
    table.sort(names)
    table.sort(implicit_aliases)
    -- table.insert(names, "(implicit)")
    -- stats["(implicit)"] = { tag = { aliases = implicit_aliases }, count = implicit_cnt }
    local str = ""..
        "{| class=\"article-table sortable\"\n"..
        "|+\n"..
        "! data-sort-type=\"text\" | Tag\n"..
        "! data-sort-type=\"number\" | Quote Count\n"..
        "! data-sort-type=\"text\" | Aliases\n"
    for _, name in ipairs(names) do
        str = str..
            "|-\n"..
            "| "..name.."\n"..
            "| "..stats[name].count.."\n"..
            "| "
        local has_aliases = false
        for _, alias in ipairs(stats[name].tag.aliases) do
            if alias ~= name then
                if has_aliases then
                    str = str.."; "
                end
                has_aliases = true
                str = str..alias
            end
        end
        if not has_aliases then str = str.."(none)" end
        str = str.."\n"
    end
    return str.."|}"
end


function m.random_wot_quote(frame)
	return m_utils.invoke_api(frame, m._random_wot_quote, "_random_wot_quote", { tags = { "1" } })
end

function m.render_all_wot_quotes(frame)
    -- TODO update to use a search with "!WOT"
	local args = m_utils.get_merged_args(frame)
	args = m_utils._map_union(args, { debug = false, tags = "all" })
    args.quotes = m._search_wot_quotes(frame, args)
    local status, result = pcall(m_quote._render_quotes, frame, args)
    if status then
        return result
    end
    return m_utils._error(frame,
        "render_all_wot_quotes failed with the following input:\n"..
        m_utils._format_code(frame, m_utils._serialize(frame.args))..
        "'''CAUSE:''' "..result.."\n")
end

function m.render_wot_quote_search(frame)
	return m_utils.invoke_api(frame, m._render_wot_quote_search, "_render_wot_quote_search", { tags = { "1" } })
end

function m.render_wot_quotes(frame)
	local args = m_utils.get_merged_args(frame)
	args = m_utils._map_union(args, { debug = false })
    args.quotes = m._search_wot_quotes(frame, args)
    local status, result = pcall(m_quote._render_quotes, frame, args)
    if status then
        return result
    end
    return m_utils._error(frame,
        "render_wot_quotes failed with the following input:\n"..
        m_utils._format_code(frame, m_utils._serialize(frame.args))..
        "'''CAUSE:''' "..result.."\n")
end

function m.search_wot_quotes(frame)
	return m_utils.invoke_api(frame, m._search_wot_quotes, "_search_wot_quotes")
end

function m.wot_quotes(frame)
	local args = m_utils.get_merged_args(frame)
	args = m_utils._map_union(args, { debug = false } )
    args.quotes = m._search_wot_quotes(frame, args)
    local status, result = pcall(m_quote._render_quotes, frame, args)
    if status then
        return result
    end
    return m_utils._error(frame,
        "wot_quotes failed with the following input:\n"..
        m_utils._format_code(frame, m_utils._serialize(frame.args))..
        "'''CAUSE:''' "..result.."\n")
end

function m.wot_stats(frame)
	return m_utils.invoke_api(frame, m._wot_stats, "_wot_stats")
end

return m