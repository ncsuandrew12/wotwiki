local m_utils = require("Module:Utils")
local m_ref = require("Module:Ref")
local m_otd_json = mw.loadJsonData('Module:OT/old_tongue_dictionary.json')
local m = {}

m.fields = {
	["Old Tongue"] = "word",
	["Definition"] = nil,
	["Common Tongue"] = "wotwiki_common",
	["Literal Translation"] = "wotwiki_literal",
	["Notes"] = "notes",
	["Parts of Speech"] = "parts"
}

function m._check_subentry_filters(frame, args, entry, se)
	if m_utils._is_true_ex(args.companion_only) and not (se.definition and se.definition.companion_epub_md) then
		return false
	end
	if m_utils._is_true_ex(args.wotwiki_common_only) and not (se.definition and se.definition.wotwiki_common) then
		return false
	end
	if m_utils._is_true_ex(args.wotwiki_literal_only) and not (se.definition and se.definition.wotwiki_literal) then
		return false
	end
	if m_utils._is_true_ex(args.compound_only) then
		for _, part in ipairs(se.parts or entry.parts or {}) do
			if part.type == "compound" then
				return true
			end
		end
		return false
	end
	if m_utils._is_true_ex(args.no_compounds) then
		for _, part in ipairs(se.parts or entry.parts or {}) do
			if part.type == "compound" then
				return false
			end
		end
	end
	return true
end

function m._get_parts_array(frame, args, entry)
	parts = {}
	for _, se in ipairs(entry.entries or { entry }) do
		for _, part in ipairs(se.parts or {}) do
			table.insert(parts, part)
		end
	end
	if #parts == 0 then return nil end
end

function m._get_parts_se(frame, args, se, text)
	-- mw.log("Getting parts for "..args.word.." parts: "..m_utils._serialize(se.parts))
	for _, part in ipairs(se.parts or {}) do
		text = text..(string.len(text) > 0 and ", " or "")..part.type
		for _, modifier in ipairs(part.modifiers or {}) do
			text = text.." ("..modifier..")"
		end
	end
	return text
end

function m._get_parts(frame, args)
	entry = m_otd_json[args.word]
	if entry == nil then return nil end
	text = ""
	for _, se in ipairs(entry.entries or { entry }) do
		text = m._get_parts_se(frame, args, se, text)
	end
	return text
end

-- Useful test code:
-- print(p._get_parts(mw.getCurrentFrame(), { word="ajah" }))
function m.get_parts(frame)
	return m_utils.invoke_api(frame, m._get_parts, "_get_parts")
end

function m._get_definition_str(frame, args, se, fields)
	-- mw.log("Getting definition: "..m_utils._serialize(se.definition))
	if fields == nil then fields = { "wotwiki_common", "wotwiki_custom", "wotwiki_literal", "wotwiki", "companion", "companion_epub_md" } end
	if not se or not se.definition then return nil end
	for _, field in ipairs(fields) do
		if se.definition[field] then
			return se.definition[field]
		end
	end
	for k, v in pairs(se.definition) do
		if type(v) == "string" then
			return v
		end
	end
	return nil
end

-- Useful test code:
-- print(p._get_definitions_str(mw.getCurrentFrame(), { word="ajah" }))
function m._get_definitions_str(frame, args)
	entry = m_otd_json[args.word]
	if entry == nil then return nil end
	definitions = {}
	for _, se in ipairs(entry.entries or { entry }) do
		def = m._get_definition_str(frame, args, se, nil)
		if (def ~= nil) then table.insert(definitions, def) end
	end
	if #definitions == 0 then return nil end
	text = ""
	for i, definition in ipairs(definitions) do
		if i > 1 then
			if not m_utils._str_ends_punct(definition) then
				text = text..";"
			end
			text = text.." "
		end
		text = text..definition
	end
	return text
end

function m.get_definition(frame)
	return m_utils.invoke_api(frame, m._get_definitions_str, "_get_definitions_str")
end

-- Useful test code:
-- print(p._get_entry_str(mw.getCurrentFrame(), { word="ajah" }))
function m._get_entry_str(frame, args)
	-- mw.log("Getting entry for "..args.word)
	if m_otd_json[args.word] then
		-- mw.log("Found entry for "..args.word)
		rendered = ""
		italicize = m._get_subentry_bool(frame, args, m_otd_json[args.word], nil, "italicize")
		rendered = rendered..(italicize and "<i>" or "").."[["..args.word.."]]"..(italicize and "</i>" or "").." -"
		for _, se in ipairs(m_otd_json[args.word].entries or { m_otd_json[args.word] }) do
			parts = m._get_parts_se(frame, args, se, "")
			txt = (parts and " (<i>"..parts.."</i>)" or "")
			txt = txt..(se.definition and (" "..(m._get_definition_str(frame, args, se, nil) or "")) or "")
			if not (m_utils._str_ends_punct(rendered) or string.match(rendered, "[-]$")) then rendered = rendered..";" end
			if not string.match(rendered, "\\s$") then rendered = rendered.." " end
			rendered = rendered..txt
		end
		-- mw.log("Returning entry: "..rendered)
		return rendered
	end
	return nil
end

function m.get_entry(frame)
	return m_utils.invoke_api(frame, m._get_entry_str, "_get_entry_str")
end

function m._get_subentry_field(frame, args, entry, se, field)
	return (se ~= nil and (se[field] ~= nil) and se[field]) or entry[field]
end

function m._get_subentry_bool(frame, args, entry, se, field)
	return m._get_subentry_field(frame, args, entry, se, field) == true
end

-- Useful test code:
-- print(p._get_wikitable(mw.getCurrentFrame(), { columns="Old Tongue;Common Tongue;Literal Translation;Parts of Speech;Notes", wotwiki_literal_only="true", no_compounds="false", compound_only="true" }))
-- print(p._get_wikitable(mw.getCurrentFrame(), { columns="Old Tongue;Common Tongue;Parts of Speech", wotwiki_common_only="true", no_compounds="true", compound_only="true", chunk="1", chunks="2" }))
-- print(p._get_wikitable(mw.getCurrentFrame(), { columns="Old Tongue;Common Tongue;Parts of Speech", wotwiki_common_only="true", no_compounds="true", compound_only="true", chunk="2", chunks="2" }))
-- print(p._get_wikitable(mw.getCurrentFrame(), { columns="Old Tongue:Word;Parts of Speech;Definition", companion_only=true }))
function m._get_wikitable(frame, args)
	-- mw.log("Getting wikitable")
	entries = {}
	columns = m_utils._parse_attribute_labels(frame, args, args.columns, m.fields)
	chunk = args.chunk and tonumber(args.chunk) or 1
	chunks = args.chunks and tonumber(args.chunks) or 1
	key_count = 0
	keys = {}
	for key, _ in pairs(m_otd_json) do
		table.insert(keys, key)
		key_count = key_count + 1
	end
	table.sort(keys)
	-- mw.log("Keys: "..m_utils._serialize(keys))
	slice = {}
	for i = math.floor((key_count * (chunk - 1)) / chunks) + 1, math.floor((key_count * chunk) / chunks) do
		table.insert(slice, keys[i])
	end
	keys = slice
	keys_chunk = {}
	for _, key in ipairs(keys) do
		entry = m_otd_json[key]
		wt = ""
		first = true
		skip = true
		for sei, se in ipairs(entry.entries or { entry }) do
			if not m._check_subentry_filters(frame, args, entry, se) then
				-- mw.log("Skipping entry "..key.."["..sei.."] due to parameters")
			else
				skip = false
				italicize = m._get_subentry_bool(frame, args, entry, se, "italicize")
				wt = wt.."|-\n"
				for _, col in ipairs(columns) do
					wt = wt.."| "
					if col.name == "Notes" then
						wt = wt..(m._get_subentry_field(frame, args, entry, se, col.field) or "")
					elseif col.name == "Common Tongue" or col.name == "Literal Translation" then
						wt = wt..(m._get_definition_str(frame, args, se, { col.field }) or "")
						for _, ref in ipairs(se.refs or {}) do
							wt = wt..m_ref._get_ref(frame, args, ref)
						end
					elseif col.name == "Definition" then
						wt = wt..(m._get_definition_str(frame, args, se, { "wotwiki", "companion", "companion_epub_md" }) or "")
					elseif col.name == "Old Tongue" then
						-- TODO: Make this entry span all the rows for the sub-entries
						wt = wt..(first and "<span id=\""..entry[col.field].."\">" or "")..
								(first and (
									(italicize and "<i>" or "")..
									"[["..entry[col.field].."]]"..
									(italicize and "</i>" or "")) or "")..
								(first and "</span>" or "")
					elseif col.name == "Parts of Speech" then
						for i, part in ipairs(se[col.field] or entry[col.field] or {}) do
							wt = wt..((i > 1) and "<br />" or "")..part.type
							for _, modifier in ipairs(part.modifiers or {}) do
								wt = wt.."<br />("..modifier..")"
							end
						end
					end
					wt = wt.."\n"
				end
				first = false
			end
		end
		if not skip then
			entries[key] = wt
			table.insert( keys_chunk, key )
		end
	end
	table.sort(keys_chunk)
	rendered = ""
	if (chunk < 2) then
		rendered = "{| class=\"wikitable sortable\"\n"
		for _, col in ipairs(columns) do
			rendered = rendered.."! "..(col.display).."\n"
		end
	else
	end
	for _, key in ipairs(keys_chunk) do
		rendered = rendered..entries[key]
	end
	if (chunk == chunks) then
		rendered = rendered.."|}"
	end
	return rendered
end

function m.get_wikitable(frame)
	return m_utils.invoke_api(frame, m._get_wikitable, "_get_wikitable")
end

return m