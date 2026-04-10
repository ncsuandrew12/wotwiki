local m_ajahs = require('Module:Ajahs')
local m_ds = require('Module:Dataset')
local m_utils = require('Module:Utils')
local m_places = require('Module:Places')
local m_chars_json = mw.loadJsonData('Module:Characters/characters.json')
local m = {}

function m._refs_wt(frame, args, refs)
	if args.suppress_refs == true then return "" end
	if refs == nil then return (args.suppress_verify == false and "{{verify}}" or "") end
	local wt = nil
	for ref_index, ref in ipairs(refs) do
		if ref.ref then
			wt = wt.."{{ref|"..ref.ref.."}}"
		elseif ref.book then
			wt = "{{ref/book|"..ref.book
			if ref.chapter then
				wt = wt.."|"..ref.chapter
			else
				wt = wt..(ref.entry and "|"..ref.entry or "")
			end
			-- TODO Add support for custom entry display text
			wt = wt.."}}"
		end
	end
	if wt == nil then return (args.suppress_verify == false and "{{verify}}" or "") end
	return wt
end

function m._copy_char_args(args)
	local nargs = {
		ajah = nil,
		all = nil,
		black_ajah = nil,
		channelers = nil,
		darkfriend = nil,
		name = nil,
		page = nil,
		sparkers = nil,
		wilders = nil,
		attributes = nil
	}
	if args.ajah then
		nargs.ajah = string.lower(args.ajah)
	end
	if args.all then
		nargs.all = m_utils._is_true_ex(args.all)
	end
	if args.black_ajah then
		nargs.black_ajah = m_utils._is_true_ex(args.black_ajah)
	end
	if args.channelers then
		nargs.channelers = m_utils._is_true_ex(args.channelers)
	end
	if args.darkfriend then
		nargs.darkfriend = m_utils._is_true_ex(args.darkfriend)
	end
	if args.name then
		nargs.name = args.name
	end
	if args.page then
		nargs.page = args.page
	end
	if args.sparkers then
		nargs.sparkers = m_utils._is_true_ex(args.sparkers)
	end
	if args.white_tower then
		nargs.white_tower = m_utils._is_true_ex(args.white_tower)
	end
	if args.wilders then
		nargs.wilders = m_utils._is_true_ex(args.wilders)
	end
	if not nargs.black_ajah and nargs.ajah == "black" then
		nargs.black_ajah = true
	end
	nargs.attributes = m_utils._parse_attribute_labels(frame, args, args.attributes or args.columns or "Name;Darkfriend;Channel;Ajah;Homeland;Spark;Wilder;Traits;Notes", nil)
	mw.log("Columns: "..(nargs.attributes and m_utils._serialize(nargs.attributes, "nargs.attributes") or "nil"))
	return nargs
end

function m._fill_character(frame, args, name, character)
	local char = m_utils._json_to_table(character)
	if char.name == nil then char.name = name end
	-- mw.log("Checking ajahs: "..(char and m_utils._serialize(char, "char") or "").." - "..(char.ajahs and m_utils._serialize(char.ajahs, "ajahs") or "").." - "..(character.ajah and m_utils._serialize(character.ajah, "ajah") or "").." - "..(character.ajah and character.ajah.ajah or ""))
	if m_utils._is_true_ex(m._get_scalar_or_epon_table_attr(frame, args, char, "aes_sedai")) then
		m._fill_character_attr(frame, args, char, "channeler", character, "aes_sedai", true)
		-- DO NOT fill in White Tower (account for AoL Aes Sedai and Seanchan archipelago Aes Sedai)
	end
	if character.ajah ~= nil then
		if type(char.ajah) ~= "table" then char.ajah = { ajah = char.ajah } end
		if char.ajahs == nil then char.ajahs = { char.ajah } end
		m._fill_character_attr(frame, args, char, "aes_sedai", character, "ajah", true)
		m._fill_character_attr(frame, args, char, "channeler", character, "ajah", true)
		-- Yes, there were non-WT ajahs that predated the white tower, but we don't have specfics on them, so they
		-- don't matter.
		m._fill_character_attr(frame, args, char, "white_tower", character, "ajah", true)
	end
	-- mw.log("Checking "..m_utils._serialize(char, "char"))
	if (m_utils._is_true_ex(m._get_scalar_or_epon_table_attr(frame, args, char, "darkfriend"))) and
		(m_utils._is_true_ex(m._get_scalar_or_epon_table_attr(frame, args, char, "aes_sedai"))) then
		if char.ajahs == nil then char.ajahs = {} end
		table.insert(char.ajahs, { ajah = "Black", refs = m._get_scalar_or_epon_table_attr_refs(frame, args, char, "darkfriend") })
		as_refs = m._get_scalar_or_epon_table_attr_refs(frame, args, character, "aes_sedai")
		if as_refs then
			char.ajahs[#char.ajahs].refs = char.ajahs[#char.ajahs].refs or {}
			for _, ref in ipairs(as_refs) do table.insert(char.ajahs[#char.ajahs].refs, ref) end
		end
		if char.black_ajah == nil then char.black_ajah = { black_ajah = true, refs = char.ajahs[#char.ajahs].refs } end
	end
	if not m_utils._is_false_ex(m._get_scalar_or_epon_table_attr(frame, args, char, "black_ajah")) then
		m._fill_character_attr(frame, args, char, "aes_sedai", character, "black_ajah", true)
		m._fill_character_attr(frame, args, char, "channeler", character, "black_ajah", true)
		m._fill_character_attr(frame, args, char, "white_tower", character, "black_ajah", true)
	end
	if m_utils._is_true_ex(m._get_scalar_or_epon_table_attr(frame, args, char, "black_ajah")) then
		m._fill_character_attr(frame, args, char, "darkfriend", character, "black_ajah", true)
	end
	if m_utils._is_true_ex(m._get_scalar_or_epon_table_attr(frame, args, char, "spark")) then
		m._fill_character_attr(frame, args, char, "channeler", character, "spark", true)
	end
	if m_utils._is_true_ex(m._get_scalar_or_epon_table_attr(frame, args, char, "wilder")) then
		m._fill_character_attr(frame, args, char, "channeler", character, "wilder", true)
	end
	if m_utils._is_true_ex(m._get_scalar_or_epon_table_attr(frame, args, char, "white_tower")) then
		m._fill_character_attr(frame, args, char, "aes_sedai", character, "white_tower", true)
		m._fill_character_attr(frame, args, char, "channeler", character, "white_tower", true)
	end
	return char
end

function m._fill_character_attr(frame, args, char, attr_name, base_char, base_attr_name, val)
	if char[attr_name] == nil or char[attr_name] == val then
		char[attr_name] = { [attr_name] = val and val or (base_char[base_attr_name] and base_char[base_attr_name]), refs = m._get_scalar_or_epon_table_attr_refs(frame, args, base_char, base_attr_name) }
	elseif type(char[attr_name]) == "table" then
		if char[attr_name][attr_name] == nil then
			char[attr_name][attr_name] = val and val or (base_char[base_attr_name] and base_char[base_attr_name])
			char[attr_name].refs = char[attr_name].refs or {}
			for _, ref in ipairs(m._get_scalar_or_epon_table_attr_refs(frame, args, base_char, base_attr_name) or {}) do
				table.insert(char[attr_name].refs, ref)
			end
		end
	else
		mw.log("WARNING: Attempting to fill character attribute "..attr_name.." with value "..tostring(val).." for character "..char.name.." but it already has non-matching value "..tostring(char[attr_name])..". Skipping.")
	end
end

function m._get_characters(frame, args, cargs)
	local keys = nil
	local chars = nil
	local chars_ready = false
	if cargs.all then
		chars = m.chars_json
	elseif cargs.name ~= nil then
		if m.chars_json[cargs.name] then
			local character = m.chars_json[cargs.name]
			if (character.name and string.lower(cargs.name) == string.lower(m_ds._get_entity_name(frame, args, character, cargs.name))) then
				chars = { [cargs.name] = character }
			end
		end
	elseif cargs.page ~= nil then
		if m.chars_json[cargs.page] then
			local character = m.chars_json[cargs.page]
			if (character.page and cargs.page == m_ds._get_entity_page(frame, args, character, cargs.page)) then
				chars = { [cargs.page] = character }
			end
		end
	else
		keys = {}
		chars = {}
		for key, character in pairs(m.chars_json) do
			-- TODO properly handle when argument is not provided, but is false
			if ((cargs.channelers == nil or (cargs.channelers == m._get_scalar_or_epon_table_attr(frame, args, character, "channeler"))) and
				(cargs.black_ajah == nil or (cargs.black_ajah == m._get_scalar_or_epon_table_attr(frame, args, character, "black_ajah"))) and
				(cargs.darkfriend == nil or (cargs.darkfriend  == m._get_scalar_or_epon_table_attr(frame, args, character, "darkfriend"))) and
				(cargs.sparkers == nil or (cargs.sparkers == m._get_scalar_or_epon_table_attr(frame, args, character, "spark"))) and
				(cargs.white_tower == nil or (cargs.white_tower == m._get_scalar_or_epon_table_attr(frame, args, character, "white_tower"))) and
				(cargs.wilders == nil or (cargs.wilders == m._get_scalar_or_epon_table_attr(frame, args, character, "wilder")))
			) then
				chars[key] = character
				table.insert(keys, key) -- Avoids an unnecessary iteration over the results
			end
		end
		chars_ready = true
	end
	if chars and keys == nil then
		keys = {}
		for key, character in pairs(chars) do
			table.insert(keys, key)
		end
	end
	table.sort(keys)
	return keys, chars
end

function m._get_table_structure(frame, args, s, t)
	for key, val in pairs(t) do
		if (s[key] == nil or type(s[key]) ~= "table") and type(val) == "table" then
			s[key] = {}
		end
		if type(val) == "table" then
			if val[1] ~= nil then
				if s[key][1] == nil then s[key][1] = {} end
				for _, v in ipairs(val) do
					m._get_table_structure(frame, args, s[key][1], v)
				end
			else
				m._get_table_structure(frame, args, s[key], val)
			end
		elseif s[key] == nil then
			s[key] = type(val)
		elseif type(s[key]) == "string" then
			types = m_utils._split(s[key], ";")
			type_exists = false
			for _, t in ipairs(types) do if t == type(val) then type_exists = true break end end
			if not type_exists then
				table.insert(types, type(val))
				table.sort(types)
			end
			s[key] = table.concat(types, ";")
		end
	end
end

-- Get the structure of the JSON file as it currently exists
function m._get_json_structure(frame, args)
	local structure = { ["name"] = {} }
	for key, character in pairs(m.chars_json) do m._get_table_structure(frame, args, structure["name"], character) end
	return structure
end

function m._get_json_structure_wt(frame, args)
	-- return m._table_to_ul(frame, args, m._get_json_structure(frame, args), 1)
	return "<pre>"..mw.text.encode(m_utils._serialize(m._get_json_structure(frame, args), nil, nil, true, true)).."</pre>"
end

function m.get_json_structure(frame)
	return m_utils.invoke_api(frame, m._get_json_structure_wt, "_get_json_structure_wt")
end

-- epon = eponymous, meaning the attribute is stored as a scalar of the same name within the table
-- Example scalar attribute: { "my_attr": true }
-- Example epon table attribute: { "my_attr": { "my_attr": true, "refs": [...] } }
function m._get_scalar_or_epon_table_attr(frame, args, entity, attr_name)
	if entity[attr_name] == nil then return nil end
	if type(entity[attr_name]) ~= "table" then return entity[attr_name] end
	if entity[attr_name][attr_name] ~= nil then return entity[attr_name][attr_name] end
	return entity[attr_name]
end

function m._get_scalar_or_epon_table_attr_refs(frame, args, entity, attr_name)
	if entity[attr_name] == nil then return nil end
	if type(entity[attr_name]) ~= "table" then return nil end
	return entity[attr_name]["refs"]
end

function m._character_entry_wt(frame, args, cargs, rargs, character, key)
	attrs = {}
	anchored = false
	page = m_ds._get_entity_page(frame, args, character, key)
	for a_i, attr in ipairs(cargs.attributes or {}) do
		wt = ""
		if attr.name == "Ajah" then
			parts = {}
			for _, ajah in ipairs(character.ajahs or {}) do
				if ajah == nil then
					mw.log("WARNING: nil ajah found for character "..character.name..". Skipping.")
				else
					table.insert(parts,
						"[["..ajah.ajah.." Ajah|"..((rargs.terse == true and m_ajahs.emoji_map[string.lower(ajah.ajah or "")]) or ajah.ajah).."]]"..
						m._refs_wt(frame, args, ajah.refs))
				end
			end
			if m._get_scalar_or_epon_table_attr(frame, args, character, "accepted") == true then
				table.insert(parts,
					"[[Accepted"..(rargs.terse == true and "|A" or "").."]]"..
					m._refs_wt(frame, args, m._get_scalar_or_epon_table_attr_refs(frame, args, character, "accepted")))
			end
			if m._get_scalar_or_epon_table_attr(frame, args, character, "novice") == true then
				table.insert(parts,
					"[[novice"..(rargs.terse == true and "|N" or "").."]]"..
					m._refs_wt(frame, args, m._get_scalar_or_epon_table_attr_refs(frame, args, character, "novice")))
			end
			wt = table.concat(parts, (rargs.is_table == true and "<br />" or " "))
		elseif attr.name == "Channel" then
			local sex = m._get_scalar_or_epon_table_attr(frame, args, character, "sex")
			if (m_utils._is_true_ex(m._get_scalar_or_epon_table_attr(frame, args, character, "channeler"))) then
				wt = "[[Channeling"..(rargs.terse == true and "|"..(sex == "male" and "🧙‍♂️" or (sex == "female" and "🧙‍♀️" or "🧙🏻")) or "").."]]"..
					m._refs_wt(frame, args,
						m._get_scalar_or_epon_table_attr_refs(frame, args, character, "channeler") or
						m._get_scalar_or_epon_table_attr_refs(frame, args, character, "spark") or
						m._get_scalar_or_epon_table_attr_refs(frame, args, character, "wilder"))
			elseif (m_utils._is_false_ex(m._get_scalar_or_epon_table_attr(frame, args, character, "channeler"))) then
				wt = ((rargs.terse == true) and ("🙎"..m._refs_wt(frame, args, m._get_scalar_or_epon_table_attr_refs(frame, args, character, "channeler")))) or ""
			else
				-- No value specified or derived, or the specified value can't be interpreted as true or false.
			end
		elseif attr.name == "Darkfriend" then
			local darkfriend = m._get_scalar_or_epon_table_attr(frame, args, character, "darkfriend")
			wt = (
				((m_utils._is_true_ex(darkfriend) == true) and "[[Darkfriend"..(rargs.terse == true and "|🖤" or "").."]]") or
				((m_utils._is_false_ex(darkfriend) == false) and "[[Light"..(rargs.terse == true and "|☀️" or "").."]]")
			) or ""
			if wt ~= "" then
				local refs = nil
				for _, attr in ipairs({ "ajah", "darkfriend" }) do
					for _, ref in ipairs(m._get_scalar_or_epon_table_attr_refs(frame, args, character, attr) or {}) do
						if refs == nil then refs = {} end
						table.insert(refs, ref)
					end
				end
				wt = wt..m._refs_wt(frame, args, refs)
			end
		elseif attr.name == "Homeland" then
			local origin = m._get_scalar_or_epon_table_attr(frame, args, character, "origin")
			if origin then
				wt = (m_places._get_place_link_wt(frame, args, origin, true) or origin)..
					m._refs_wt(frame, args, m._get_scalar_or_epon_table_attr_refs(frame, args, character, "origin"))
			end
		elseif attr.name == "Name" then
			wt = "[["..page.."]]"
		elseif attr.name == "Spark" then
			local spark = m._get_scalar_or_epon_table_attr(frame, args, character, "spark")
			wt = ((m_utils._is_true_ex(spark) and "[[Spark"..(rargs.terse == true and "|🎆" or "").."]]") or
				((rargs.terse == true) and m_utils._is_false_ex(spark) and "🙎") or "")..
				m._refs_wt(frame, args, m._get_scalar_or_epon_table_attr_refs(frame, args, character, "spark"))
		elseif attr.name == "Traits" then
		elseif attr.name == "Wilder" then
			local wilder = m._get_scalar_or_epon_table_attr(frame, args, character, "wilder")
			if wilder ~= nil then
				wt = ((m_utils._is_true_ex(wilder) and "[[Wilder"..(rargs.terse == true and "|🧠" or "").."]]") or (m_utils._is_false_ex(wilder) and "[[White Tower|🏫]]") or "")..
					m._refs_wt(frame, args, m._get_scalar_or_epon_table_attr_refs(frame, args, character, "wilder"))
			end
		elseif attr.name == "Notes" then
			wt = character.notes and (
					table.concat(type(character.notes) == "table" and character.notes or {character.notes},
					rargs.is_table == true and "<br />\n" or " ")) or ""
			wt = ((string.len(wt) > 0 and rargs.is_table == false) and "- " or "")..wt
		else
			local key = nil
			for _, c in ipairs({ attr.field, attr.name }) do if c and character[c] then key = c end end
			if key then wt = character[key]..m._refs_wt(frame, args, m._get_scalar_or_epon_table_attr_refs(frame, args, character, key)) end
		end
		if (rargs.is_table == false) and (string.len(wt) > 0) and (a_i > 1) and (attr.name ~= "Notes") then
			wt = "("..wt..")"
		end
		if anchored == false then
			wt = "<span id=\""..(args.anchor_prefix or "")..page.."\">"..wt.."</span>"
			anchored = true
		end
		if (rargs.is_table == true) or (string.len(wt) > 0) then table.insert(attrs, wt) end
	end
	return table.concat(attrs, (rargs.delimiter or ""))
end

-- Useful test code:
-- =p._get_characters_ul(mw.getCurrentFrame(), { sparkers="True", wilders="True" })
function m._get_characters_ul(frame, args)
	local rendered = ""
	local cargs = m._copy_char_args(args)
	local keys, chars = m._get_characters(frame, args, cargs)
	rows = {}
	for _, key in ipairs(keys) do
		table.insert(rows, m._character_entry_wt(frame, args, cargs,
			{ delimiter = " ", is_table = false, terse = false }, chars[key], key))
	end
	return frame.preprocess(frame, "* "..table.concat(rows, "\n* "))
end

function m.get_characters_ul(frame)
	return m_utils.invoke_api(frame, m._get_characters_ul, "_get_characters_ul")
end

-- Useful test code:
-- =p._get_characters_wikitable(mw.getCurrentFrame(), { all="True", attributes="Ajah;Spark;Wilder;Homeland" })
function m._get_characters_wikitable(frame, args)
	local cargs = m._copy_char_args(args)
	local keys, chars = m._get_characters(frame, args, cargs)
	headers = {}
	for _, column in ipairs(cargs.attributes or {}) do
		line = nil
		if column.name == "Ajah" then
			line = "<span style=\"display:block; writing-mode:vertical-lr; transform:rotate(180deg)\">[[Ajah]]</span>"
		elseif column.name == "Channel" then
			line = "<span style=\"display:block; writing-mode:vertical-lr; transform:rotate(180deg)\">[[:Category:Channelers|Channel]]</span>"
		elseif column.name == "Darkfriend" then
			line = "<span style=\"display:block; writing-mode:vertical-lr; transform:rotate(180deg)\">[[Darkfriend]]</span>"
		elseif column.name == "Spark" then
			line = "<span style=\"display:block; writing-mode:vertical-lr; transform:rotate(180deg)\">[[Spark]]</span>"
		elseif column.name == "Wilder" then
			line = "<span style=\"display:block; writing-mode:vertical-lr; transform:rotate(180deg)\">[[Wilder]]</span>"
		else
			line = column.name
		end
		table.insert(headers, line)
	end
	rows = {}
	for _, key in ipairs(keys) do
		table.insert(rows, m._character_entry_wt(frame, args, cargs,
			{ delimiter = "\n| ", is_table = true, terse = true },
			chars[key], key, true))
	end
	return frame.preprocess(frame,
		"{| class=\"wikitable sortable\"\n! "..
		table.concat(headers, "\n! ")..
		"\n|-\n| "..
		table.concat(rows, "\n|-\n| ")..
		"\n|}")
end

function m.get_characters_wikitable(frame)
	return m_utils.invoke_api(frame, m._get_characters_wikitable, "_get_characters_wikitable")
end

-- Useful test code:
-- =p._get_character_ibox(mw.getCurrentFrame(), { sparkers="True", wilders="True" })
function m._get_character_ibox(frame, args)
	local rendered = ""
	local chars = m._get_characters(frame, args, m._copy_char_args(args))
	for key, character in pairs(chars) do
		rendered = rendered.."* [["..m_ds._get_entity_page(frame, args, character, key).."]]"
		rendered = rendered.."\n"
	end
	return frame.preprocess(frame, rendered)
end

function m.get_character_ibox(frame)
	return m_utils.invoke_api(frame, m._get_character_ibox, "_get_character_ibox")
end

m.chars_json = {}
for key, character in pairs(m_chars_json) do
	mw.log("Processing character: "..key)
	m.chars_json[key] = m._fill_character(nil, nil, key, character)
end

return m