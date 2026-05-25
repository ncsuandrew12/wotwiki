local _module_prefix = ""
-- _module_prefix = 'Sandbox/androlf/'
local m_utils = require('Module:'.._module_prefix..'Utils')
local m_quote = require('Module:'.._module_prefix..'Quote')
local m_wotq = require('Module:'.._module_prefix..'WotQ')

local m = {}

function m._quote_of_the_day(frame, args)
    -- As changes are made to regular quote formatting, update this to preserve
    -- QOTD formatting
    local s = args and "true" or "false"
    mw.log("args: "..s)
    local render_args = {}
    for key, value in pairs(args) do
        render_args[key] = value
    end
    if not args["quote_margins"] then
        mw.log("Setting quote_margins to false")
        render_args["quote_margins"] = "false"
    end
    if not args["quote_width"] then
        mw.log("Setting quote_width to nil")
        render_args["quote_width"] = "nil"
    end
    if not args["quote_border"] then
        mw.log("Setting quote_border to empty string")
        render_args["quote_border"] = "nil"
    end
    if not args["quote_render_refs"] then
        mw.log("Setting quote_render_refs to false")
        render_args["quote_render_refs"] = "false"
    end
	render_args = m_utils._map_union(render_args, { debug = false, quotes = { m._select_quote_of_the_day(frame) } })
    return m_quote._render_quotes(frame, render_args, false)
end

function m._quote_of_the_day_by_day(frame)
    local year = os.date("!*t").year
    local start_date = os.time({year = year, month = 1, day = 1, hour = 0, min = 0, sec = 0})
    local end_date = os.time({year = year + 1, month = 1, day = 1, hour = 0, min = 0, sec = 0})
    local all_quotes = m._select_all_quotes_of_the_day(frame, frame.args)
    local quotes = {}
    for date = start_date, end_date - 1, 24 * 60 * 60 do
        local date_table = os.date("!*t", date)
        if date_table.day == 1 then
            quotes[date_table.month] = {}
        end
        -- TODO: Update _select_quote_of_the_day to support date types and pass date
        -- directly without converting to string.
        quotes[date_table.month][date_table.day] = {
            date = date,
            quote = m._select_quote_of_the_day(frame,
                date,
                all_quotes
            )
        }
    end
    return quotes
end

function m._quote_of_the_day_by_speaker(frame)
	local args = m_utils.get_merged_args(frame)
    -- TODO Switch from per-speaker subsections to a single section with links
    -- to each speaker at the top of the section.
    local all_quotes = m._select_all_quotes_of_the_day(frame, args)
    local str = "==By speaker=="
    local speakers = {}
    local quotes_by_speaker = { Miscellaneous = {} }
    for _, quote in ipairs(all_quotes) do
        if quote.speakers then
            for _, speaker in ipairs(quote.speakers) do
                if not quotes_by_speaker[speaker.name] then
                    quotes_by_speaker[speaker.name] = {}
                    local add = true
                    for _, s in ipairs(speakers) do
                        if speaker.name == s then
                            add = false
                            break
                        end
                    end
                    if add then table.insert(speakers, speaker.name) end
                end
                local add = true
                for _, q in ipairs(quotes_by_speaker[speaker.name]) do
                    if q.index == quote.index then
                        add = false
                        break
                    end
                end
                if add then table.insert(quotes_by_speaker[speaker.name], quote) end
            end
        else
            local add = true
            for _, q in ipairs(quotes_by_speaker.Miscellaneous) do
                if q.index == quote.index then
                    add = false
                    break
                end
            end
            if add then table.insert(quotes_by_speaker.Miscellaneous, quote) end
        end
    end
    table.sort(speakers)
    table.insert(speakers, "Miscellaneous")
    -- table.sort(quotes_by_speaker)
    for _, speaker in pairs(speakers) do
        str = str..string.format("\n\n===[[%s]]===", speaker)
        for _, q in ipairs(quotes_by_speaker[speaker]) do
        	args.q = q
            str = str.."\n\n"..m_quote._render_quote(frame, args)
        end
    end
    return str
end

function m._quote_of_the_day_calendar(frame)
	local args = m_utils.get_merged_args(frame)
    local months = m._quote_of_the_day_by_day(frame)
    local str = "==By month=="
    local q_str = "==Quotes=="
    local lang = mw.language.getContentLanguage()
    for m, days in ipairs(months) do
        str = str..string.format("\n\n===%s===\n", lang:formatDate("F", "@"..days[1].date))
        local first_day = true
        for d, q in ipairs(days) do
            args.q = q.quote
            str = str..(first_day and "" or " ")
            first_day = false
            local anchor = ""..m.."_"..d
            str = str.."[[#"..anchor.."|"..d.."]]"
            q_str = q_str.."\n\n<span id=\""..anchor.."\">"..lang:formatDate("F j", "@"..q.date).."</span> [[#top|^]]\n"..
                m_quote._render_quote(frame, args)
        end
    end
    return str.."\n\n"..q_str
end

function m._select_all_quotes_of_the_day(frame, args)
    mw.log("args: "..(args and "true" or "false"))
    local select_args = {}
    if not args["tags"] or string.len(args["tags"]) == 0 then
        select_args["tags"] = "all\n!QOTD"
        mw.log("Set tags to "..select_args["tags"])
    end
    return m_wotq._search_wot_quotes(frame, select_args)
end

function m._select_quote_of_the_day(frame, date, quotes)
    local random_args = {}
    for key, value in pairs(frame.args) do
        random_args[key] = value
    end
    if not frame.args["random_seed"] then
        local datetime = nil
        if date then
            datetime = date
        elseif frame.args["date"] and string.len(frame.args["date"]) > 0 then
            datetime = m_utils._parse_date(frame, frame.args["date"])
        else
            datetime = os.time()
        end
        random_args["random_seed"] = ""..math.floor(datetime/(24*60*60))
        mw.log("Set random_seed to epoch days ("..random_args["random_seed"]..")")
    end
    if not quotes then quotes = m._select_all_quotes_of_the_day(frame, frame.args) end
    return m_utils._select_random_entry(frame, random_args, quotes)
end

function m.quote_of_the_day(frame)
	return m_utils.invoke_api(frame, m._quote_of_the_day, "_quote_of_the_day")
end

function m.quote_of_the_day_by_speaker(frame)
	return m_utils.invoke_api(frame, m._quote_of_the_day_by_speaker, "_quote_of_the_day_by_speaker")
end

function m.quote_of_the_day_calendar(frame)
	return m_utils.invoke_api(frame, m._quote_of_the_day_calendar, "_quote_of_the_day_calendar")
end

return m