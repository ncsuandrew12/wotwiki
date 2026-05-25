local _module_prefix = ""
-- _module_prefix = 'Sandbox/androlf/'
local m_utils = require('Module:'.._module_prefix..'Utils')
local m_mbox = require('Module:Mbox')

local m = {}

m.Test_quotes = {
    {
    }, {
        quote = "Quotation -1",
        topic = "topic"
    }, {
        quote = "Quotation 0",
        early_refs = {
            { "ref", { "[https://wot.fandom.com Link1]", "link1" } },
            { "ref", { "", "link1" } },
            { "ref", { "[https://wot.fandom.com Link2]" } },
        },
        description = "Speaker",
        topic = "topic",
        book_refs = { { 1, 2 }, { 3, 4 } },
        other_refs = {
            "{{ref|[https://wot.fandom.com Link3]}}",
            "{{ref|[https://wot.fandom.com Link4]}}",
        },
    }, {
        quote = "Quotation 1",
    }, {
        quote = "Quotation 2",
        description = "Speaker",
    }, {
        quote = "Quotation 3",
        description = "Speaker",
        topic = "topic"
    }, {
        quote = "Quotation 5",
        book_refs = { { 1, 2 } },
    }, {
        quote = "Quotation 6",
        book_refs = { { 1, 2 }, { 3, 4 } },
    }, {
        quote = "Quotation 7",
        other_refs = {
            "{{ref|[https://wot.fandom.com Link1]}}",
            "{{ref|[https://wot.fandom.com Link2]}}",
        },
    },
    {
        quote = "Quotation 8",
        early_refs = {
            { "ref", { "[https://wot.fandom.com Link1]" } },
            "{{ref|[https://wot.fandom.com Link2]}}",
        }
    }, {
        quote = "Quotation 9",
        book_refs = {
            { 1, 2 },
            { 3, 4 },
        },
        other_refs = {
            "{{ref|[https://wot.fandom.com Link1]}}",
            "{{ref|[https://wot.fandom.com Link2]}}",
        },
    }, {
        quote = "Quotation 10",
        description = "[https://wot.fandom.com Link1]",
        other_refs = { "{{ref|[https://wot.fandom.com Link2]}}" },
    }
}

function m._process_quote_text(text, starts_italicized, invert_italics, strip_wiki_links, br_newlines)
    if invert_italics then
        local italics = starts_italicized
        while true do
            local matches = 0
            local repl = italics and "</i>" or "<i>"
            text, matches = string.gsub(text, "'''''", italics and repl.."'''" or "'''"..repl, 1)
            if matches == 0 then
                text, matches = string.gsub(text, "^''([^'])", repl.."%1", 1)
            end
            if matches == 0 then
                text, matches = string.gsub(text, "([^'])''$", "%1"..repl, 1)
            end
            if matches == 0 then
                text, matches = string.gsub(text, "([^'])''([^'])", "%1"..repl.."%2", 1)
            end
            if matches > 0 then
                italics = not italics
            end
            if matches == 0 then break end
        end
    end
    if strip_wiki_links then
        text, _ = string.gsub(text, "%[%[[^%|%]]+%|([^%]]+)%]%]", "%1")
        text, _ = string.gsub(text, "%[%[([^%|%]]+)%]%]", "%1")
    end
    if br_newlines then
        text, _ = string.gsub(text, "\n", "<br />")
    end
    return text
end

m.local_aliases = {}

function m._dealias_tag(frame, tag)
    if type(tag) == "table" then return tag end
    if not m.local_aliases[tag] then m.local_aliases[tag] = { name = tag, page = tag, short = tag } end
    return m.local_aliases[tag]
end

function m._quote(frame, args)
    if not args or (not args.quote and not args.interchange) then
        error("Missing quote parameter!")
        return nil
    end
    local other_refs_str = nil
    local participants = nil
    local quote = {}
    if args.quote then quote.quote = args.quote end
    if args.interchange then
        local line_i = 1
        local interchange = {}
        local participant = nil
        for line in string.gmatch(args.interchange, "[^\r\n]+") do
            mw.log("Quote interchange line: "..line)
            if math.fmod(line_i, 2) == 1 then
                local trimmed = mw.text.trim(line)
                participant = m._dealias_tag(frame, trimmed)
                local lower = string.lower(trimmed)
                if lower ~= "question" and lower ~= "answer" and lower ~= "fan" and lower ~= "q" and lower ~= "a" then
                    participants = m_utils._table_union(participants, { participant })
                end
            else
                table.insert(interchange, { participant = participant, text = line })
            end
            line_i = line_i + 1
        end
        quote.quote = interchange
        quote.interchange = nil
    end
    for key, value in pairs(args) do
        if key == "quote" or (key == 1 and args.interchange == nil) then
            -- Already handled by caller
        elseif key == "speakers" then
            if string.len(value) > 0 then
                for tag in string.gmatch(value, "[^\r\n]+") do
                    tag = m._dealias_tag(frame, mw.text.trim(tag))
                    if tag then
                        quote.speakers = m_utils._table_insert_or_create(quote.speakers, tag)
                    end
                end
            end
        elseif key == "addressees" then
            if string.len(value) > 0 then
                for tag in string.gmatch(value, "[^\r\n]+") do
                    tag = m._dealias_tag(frame, mw.text.trim(tag))
                    if tag then
                        quote.addressees = m_utils._table_insert_or_create(quote.addressees, tag)
                    end
                end
            end
        elseif key == "pseudosource" then
            if string.len(value) > 0 then
                quote.pseudosource = m._dealias_tag(frame, mw.text.trim(value))
            end
        elseif key == "description" or (key == 2 and args.interchange == nil) then
            if string.len(value) > 0 then quote.description = value end
        elseif key == "topic" or (key == 3 and args.interchange == nil) then
            if string.len(value) > 0 then quote.topic = value end
        elseif key == "other_refs" or (key == 4 and args.interchange == nil) then
            if string.len(value) > 0 then
                other_refs_str = value
            end
        elseif key == "early_refs" or (key == 5 and args.interchange == nil) then
            if string.len(value) > 0 then
                quote.early_refs = m_utils._table_insert_or_create(quote.early_refs, value)
            end
        end
    end
    if not quote.speakers and participants then
        quote.speakers = participants
    end
    if other_refs_str then
        -- if not quote.description and not quote.speakers and not quote.pseudosource then
        --     quote.description = ''
        -- end
        quote.other_refs = m_utils._table_insert_or_create(quote.other_refs, other_refs_str)
    end
    args.debug = false
    args.quotes = { quote }
    return m._render_quotes(frame, args)
end

function m._quote_interchange(frame, args)
    if not args.quote then
        error("Missing quote text!")
        return nil
    end
    args.interchange = args.quote
    args.quote = nil
    return m._quote(frame, args)
end

-- Format a quote for display
-- @param frame The frame mect to use for template expansion
-- @param q The quote to format, as a key-value table with a subset of the following keys:
--   { quote, description, early_refs, topic, book_refs, other_refs }
function m._render_quote(frame, args)
    assert(args.q ~= nil, "No quote provided!")
    local quote = nil
    local early_refs = nil
    local speakers = nil
    local addressees = nil
    local pseudosource = nil
    local description = nil
    local description_extra = nil
    local topic = nil
    local book_refs = nil
    local other_refs = nil
    local quote_border = nil
    local quote_marks = true -- TODO For new style, switch to false
    local quote_margins = true
    local quote_width = nil
    local render_refs = true
    local render_description = true
    quote_border = "1px solid #af5a1f;"
    quote_width = "50%"
    for key, value in pairs(args) do
        if type(value) == "table" then
        	mw.log("table arg: "..key)
    	else
	        local value_lc = nil
	        if type(value) == "string" then
	        	string.lower(value)
        	elseif type(value) == "boolean" then
        		value = value and "true" or "false"
        		value_lc = value_lc
    		else
    			error("Unsupported value type: "..type(value))
    			return nil
    		end
	        if key == "quote_border" and string.len(value) > 0 then
	    		if value == "nil" then
	    			quote_border = nil
				else
	        		quote_border = value
	    		end
	        	if quote_border then mw.log("Parsed quote_border: "..quote_border) end
	        elseif key == "quote_marks" and string.len(value) > 0 then
	            quote_marks = value_lc == "true" and true or false
	            mw.log("Parsed quote_marks: "..tostring(quote_marks))
	        elseif key == "quote_margins" and string.len(value) > 0 then
	            quote_margins = value_lc == "true" and true or false
	            mw.log("Parsed quote_margins: "..tostring(quote_margins))
	        elseif key == "quote_width" and string.len(value) > 0 then
	    		if value == "nil" then
	    			quote_width = nil
				else
	        		quote_width = value
	    		end
	        	if quote_width then mw.log("Parsed quote_width: "..quote_width) end
	        elseif key == "quote_render_refs" and string.len(value) > 0 then
	            render_refs = value_lc == "true" and true or false
	            mw.log("Parsed render_refs: "..tostring(render_refs))
	        elseif key == "quote_render_description" and string.len(value) > 0 then
	            render_description = value_lc == "true" and true or false
	            mw.log("Parsed render_description: "..tostring(render_description))
	        else
	            mw.log("Irrelevant arg in _render_quote: "..key..": "..value)
	        end
        end
    end
    for key, value in pairs(args.q) do
        if key == "quote" then
            quote = value
        elseif key == "early_refs" then
            early_refs = value
        elseif key == "speakers" then
            speakers = value
        elseif key == "addressees" then
            addressees = value
        elseif key == "pseudosource" then
            pseudosource = value
        elseif key == "description" then
            if string.len(value) > 0 then description = value end
        elseif key == "description_extra" then
            if string.len(value) > 0 then description_extra = value end
        elseif key == "topic" then
            if string.len(value) > 0 then topic = value end
        elseif key == "book_refs" then
            book_refs = value
        elseif key == "other_refs" then
            other_refs = value
        elseif key == "tags" then
            -- Not used when rendering quotes; used for filtering/searching
        elseif key == "index" then
            -- Not used when rendering quotes
        else
            mw.log("WARNING: Unknown quote field: "..key)
        end
    end
    if not quote then
        error("Missing quote text!\n"..(args and m_utils._format_code(frame, m_utils._serialize(args, "args")) or "nil args"))
        return nil
    end
    local ref_str = nil
    local nonbook_refs = false
    if render_refs and other_refs then
        ref_str = ''
        for _, r in ipairs(other_refs) do
            nonbook_refs = true
            ref_str = ref_str..r
        end
    end
    if render_refs and book_refs then
        if not ref_str then
            ref_str = ''
        end
        for _, r in ipairs(book_refs) do
            ref_str = ref_str.."{{ref/book"
            for _, v in ipairs(r) do
                ref_str = ref_str.."|"..v
            end
            ref_str = ref_str.."}}"
        end
    end
    local early_ref_str = nil
    if render_refs and early_refs then
        early_ref_str = ''
        for _, r in ipairs(early_refs) do
            if type(r) == "table" then
                early_ref_str = early_ref_str.."{{"..r[1]
                if type(r[2]) == "table" then
                    for _, v in ipairs(r[2]) do
                        early_ref_str = early_ref_str..string.format("|%s", v)
                    end
                elseif r[2] then
                    early_ref_str = early_ref_str..string.format("|%s", r[2])
                end
                early_ref_str = early_ref_str.."}}"
            else
                early_ref_str = early_ref_str..r
            end
        end
    end
    local top_div_class = nil
    if type(quote) == "string" then
        top_div_class = "quote"
    elseif type(quote) == "table" then
        top_div_class = "quote_interchange"
    else
        error("Unknown quote type: "..type(quote))
    end
    local font_size = 95
    if type(quote) == "string" then
        local ql = nil
        local nl = 0
        ql, _ = string.gsub(mw.text.killMarkers(quote), "<[^>]+>", "")
        _, nl = string.gsub(ql, "\n", "\n")
        if string.len(ql) > 350 or nl > 5 then
            font_size = 85
        end
    end
    -- Regular wiki text causes a good bit of space to be between the previous
    -- text androlf the top border of the quote box. So we should have a
    -- comparable margin-bottom.
    local margin_style = quote_margins and "margin-left: 50px; margin-top:5px; margin-bottom:20px; padding:10px; padding-top:5px; padding-bottom:5px;" or ""
    local quote_border_str = ""
    if quote_border then quote_border_str = "border: "..quote_border..";" end
    local quote_width_str = quote_width and "max-width:"..quote_width..";" or ""
    -- TODO figure out how to get border to surround short quotes "tightly"?
    local quote_mark_span = string.format(
        "<span class=\"quote-quote\" style=\"font-family: 'Times New Roman',serif; font-weight: bold; font-size:%d%%;\">",
        math.floor((type(quote) == "string" and 1.4 or 1) * font_size))
    local quote_marks_str_open = ""
    local quote_marks_str_close = ""
    if quote_marks then
        quote_marks_str_open = quote_mark_span.."“</span>"
        quote_marks_str_close = quote_mark_span.."”</span>"
    end
    local mbox_args = { class = "quotebox hidden", bordercolor = "#af5a1f;", bgcolor = "#141414;", text = "" }
    local rendered_mobile = string.format("<blockquote class=\"desktop-hidden\">")
    local speaker_cnt = 0
    if speakers then table.maxn(speakers) end
    if type(quote) == "string" then
    	local quote_text = m._process_quote_text(quote, false, false, true, true)
	    mbox_args.text = mbox_args.text.."<nowiki/>''<nowiki/>"..quote_text.."<nowiki/>''<nowiki/>"
    	rendered_mobile = rendered_mobile.."<nowiki/>''<nowiki/>"..quote_text.."<nowiki/>''<nowiki/>"
    	if render_refs then
		    if early_ref_str then
		    	mbox_args.text = mbox_args.text..early_ref_str
		    	rendered_mobile = rendered_mobile..early_ref_str
		    	early_ref_str = nil
		    end
	    	if ref_str and not description and not speakers and not pseudosource and not nonbook_refs then
		    	mbox_args.text = mbox_args.text..ref_str
		    	rendered_mobile = rendered_mobile..ref_str
		        ref_str = nil
	        end
	    end
    elseif type(quote) == "table" then
        local interchange_table = "<table style=\"margin: 0; padding:0;\">\n"
	    for _, line in ipairs(quote) do
            local add_quotes = line.quote_marks == nil and true or line.quote_marks
            interchange_table = interchange_table.."<tr>\n"
            mw.log("Quote interchange entry: "..line.participant.short..": "..line.text)
            -- TODO make participant text a non-formatted link.
            interchange_table = interchange_table..string.format(
                "<td style=\"text-align: right; vertical-align: top;\">'''%s''':</td>\n"..
                    "<td style=\"vertical-align: top;\">%s%s%s</td>",
                    line.participant.short,
                add_quotes and "“" or "",
                m._process_quote_text(line.text, false, false, true, true),
                add_quotes and "”" or "")
            local new = true
            interchange_table = interchange_table.."</tr>\n"
    	end
        interchange_table = interchange_table.."</table>"
        local processed_interchange_table = interchange_table
        mbox_args.text = mbox_args.text..processed_interchange_table
	    rendered_mobile = rendered_mobile..processed_interchange_table
	    if render_refs and early_ref_str then
	    	mbox_args.text = mbox_args.text..early_ref_str
	    	rendered_mobile = rendered_mobile..early_ref_str
	    	early_ref_str = nil
	    end
	end
    local byline = nil
    local rendered_description = nil
    if render_description then
        if not description then
            if speakers then
                byline = ''
                for i, speaker in ipairs(speakers) do
                    if i > 1 then
                        if speaker_cnt > 2 then
                            if (i == speaker_cnt) then
                                byline = byline..", and "
                            else
                                byline = byline..", "
                            end
                        else
                            byline = byline.." and "
                        end
                    end
                    byline = byline..string.format("[[%s|%s]]", speaker.page, speaker.name)
                end
                if addressees then
                    byline = byline.." to "
                    local addressees_cnt = 0
                    for _, _ in ipairs(addressees) do addressees_cnt = addressees_cnt + 1 end
                    for i, addressee in ipairs(addressees) do
                        local db_addressee = m._dealias_tag(frame, addressee)
                        if i > 1 then
                            if addressees_cnt > 2 then
                                if (i == addressees_cnt) then
                                    byline = byline..", and "
                                else
                                    byline = byline..", "
                                end
                            else
                                byline = byline.." and "
                            end
                        end
                        byline = byline..string.format("[[%s|%s]]", db_addressee.page, db_addressee.name)
                    end
                end
            end
            if pseudosource then
                if byline then
                    byline = byline.." in "
                else
                    byline = "From "
                end
                local db_pseudosource = m._dealias_tag(frame, pseudosource)
                byline = byline..string.format("''[[%s|%s]]''", db_pseudosource.page, db_pseudosource.name)
            end
        end
        if not description and byline then
        	description = byline
        	byline = nil
    	end
        if description_extra then
        	description = (description and description or '')..description_extra
        	description_extra = nil
    	end
        if description then
        	rendered_description = description
        	description = nil
    	end
        if topic then
            if rendered_description then
                rendered_description = rendered_description.."&nbsp;''on "..topic.."<nowiki/>''<nowiki/>"
            else
                rendered_description = "<nowiki/>''<nowiki/>"..topic.."<nowiki/>''<nowiki/>"
            end
            topic = nil
        end
	    if render_refs and ref_str and rendered_description then
	    	rendered_description = rendered_description..ref_str
	        ref_str = nil
	    end
        if type(quote) == "string" and rendered_description then rendered_mobile = rendered_mobile.."<br />" end
        if rendered_description then
        	mbox_args.comment = rendered_description
        	rendered_mobile = rendered_mobile.."&mdash;&nbsp;"..rendered_description
    	end
    end
    if render_refs and ref_str then 
    	if mbox_args.comment then
    		mbox_args.comment = mbox_args.comment..ref_str
		else
			-- Even though no early_refs were provided, it would look wonky to have pure superscript on the
			-- description line, so we put the refs with the quote text instead.
    		mbox_args.text = mbox_args.text..ref_str
    	end
		ref_str = nil
    end
    for _, v in ipairs({ "text", "comment" }) do if mbox_args[v] then mbox_args[v] = frame.preprocess(frame, mbox_args[v]) end end
    frame.args = mbox_args
    return tostring(m_mbox.main(frame))..frame.preprocess(frame, rendered_mobile.."</blockquote>") 
end

function m._render_quotes(frame, args)
    local str = nil
    for _, q in ipairs(args.quotes) do
        if (str == nil) then
            str = ''
        else
            str = str.."\n\n"
        end
        args.q = q
        if args.debug then str = str..m_utils._format_code(frame, m_utils._serialize(q)).."\n\n" end
        local status, quote = pcall(m._render_quote, frame, args)
        if status then
            str = str..quote
        else
            str = str..m_utils._error(frame, "Quote rendering failed for the following quote input:\n"..
                m_utils._format_code(frame, m_utils._serialize(q)).."\n"..
                m_utils._format_code(frame, m_utils._serialize(args)).."\n"..
                "'''CAUSE:''' "..quote)
        end
    end
    return str
end

function m.quote(frame)
	return m_utils.invoke_api(frame, m._quote, "_quote", { quote = { "1" }, description_extra = { "2" }, topic = { "3" }, other_refs = { "4" }, early_refs = { "5" } })
end

function m.quote_interchange(frame)
	return m_utils.invoke_api(frame, m._quote_interchange, "_quote_interchange", nil) -- 'quote' and '1' are equivalent, but {{{1}}} from the template isn't equivalent to quote
end

function m.render_test_quotes(frame)
	local args = m_utils.get_merged_args(frame)
	args = m_utils._map_union(args, { debug = true, quotes = m.Test_quotes })
    local status, result = pcall(m._render_quotes, frame, args)
    if status then
        return result
    end
    return m_utils._error(frame,
        "render_test_quotes failed with the following input:\n"..
        m_utils._format_code(frame, m_utils._serialize(args))..
        "'''CAUSE:''' "..result.."\n")
end

return m