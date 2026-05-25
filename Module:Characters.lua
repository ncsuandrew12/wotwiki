local m_ajahs = require('Module:Ajahs')
local m_ds = require('Module:Dataset')
local m_utils = require('Module:Utils')
local m_places = require('Module:Places')
local m_ref = require('Module:Ref')
local m_chars_json = mw.loadJsonData('Module:Characters/characters.json')
local m = {}

function m._canonical_ref_value(value, seen)
	local t = type(value)
	if t == "nil" then return "nil" end
	if t == "number" or t == "boolean" then return tostring(value) end
	if t == "string" then return string.format("%q", value) end
	if t ~= "table" then return tostring(value) end
	seen = seen or {}
	if seen[value] then return "<cycle>" end
	seen[value] = true

	local keys = {}
	local max_index = 0
	local count = 0
	local array_like = true
	for k, _ in pairs(value) do
		count = count + 1
		if type(k) == "number" and k > 0 and math.floor(k) == k then
			if k > max_index then max_index = k end
		else
			array_like = false
		end
		table.insert(keys, k)
	end

	local parts = {}
	if array_like and max_index == count then
		for i = 1, max_index do
			table.insert(parts, m._canonical_ref_value(value[i], seen))
		end
		seen[value] = nil
		return "["..table.concat(parts, ",").."]"
	end

	table.sort(keys, function(a, b) return tostring(a) < tostring(b) end)
	for _, k in ipairs(keys) do
		table.insert(parts, m._canonical_ref_value(k, seen)..":"..m._canonical_ref_value(value[k], seen))
	end
	seen[value] = nil
	return "{"..table.concat(parts, ",").."}"
end

function m._shared_ref_name(ref_key)
	-- Small deterministic hash used only for MediaWiki ref-name stability.
	local hash = 0
	for i = 1, string.len(ref_key) do
		hash = (hash * 33 + string.byte(ref_key, i)) % 4294967291
	end
	return "charref_"..tostring(hash).."_"..tostring(string.len(ref_key))
end

function m._named_raw_ref_wt(ref_name, content)
	-- Bypass Module:Ref for plain string notes when sharing is enabled.
	-- On live Fandom/MediaWiki, Module:Ref may return a parser strip marker
	-- from frame:extensionTag rather than literal <ref>...</ref> wikitext; the
	-- previous patch could not add a name to that marker, so every note remained
	-- an independent numbered reference. Raw ref tags returned by Lua are parsed
	-- normally by MediaWiki and can therefore be safely named/reused.
	return "<ref name=\""..ref_name.."\">"..tostring(content).."</ref>"
end

function m._named_raw_ref_reuse_wt(ref_name)
	return "<ref name=\""..ref_name.."\" />"
end

function m._reset_ref_cache(args)
	if args == nil then return end
	args._shared_ref_names = {}
	args._shared_ref_can_reuse = {}
end

function m._first_named_ref_wt(ref_wt, ref_name)
	if type(ref_wt) ~= "string" then return ref_wt, false end
	-- If Module:Ref already produced a named reference, leave it untouched.
	if mw.ustring.match(ref_wt, "^%s*<ref%s+[^>]*name%s*=") then return ref_wt, false end
	-- Fandom uses standard MediaWiki/Cite refs. Preserve any non-name
	-- attributes Module:Ref may add, such as group="note", while adding a
	-- deterministic name.
	local attrs, inner = mw.ustring.match(ref_wt, "^%s*<ref([^>/]*)>(.*)</ref>%s*$")
	if inner == nil then return ref_wt, false end
	attrs = attrs or ""
	if attrs ~= "" and not mw.ustring.match(attrs, "^%s") then attrs = " "..attrs end
	return "<ref name=\""..ref_name.."\""..attrs..">"..inner.."</ref>", true
end

function m._ref_sharing_disabled(args)
	-- Sharing is on by default. Disable only when share_refs is explicitly false-like
	-- (e.g. share_refs=false or share_refs=No). On Fandom/MediaWiki, omitted
	-- template parameters are nil; treating nil as false disables this feature by
	-- accident because m_utils._is_false_ex(nil) is true in this codebase.
	return args ~= nil and args.share_refs ~= nil and m_utils._is_false_ex(args.share_refs)
end

function m._ref_wt(frame, args, ref)
	local sharing_enabled = not (args == nil or m._ref_sharing_disabled(args))
	if not sharing_enabled then return m_ref._get_ref(frame, args, ref) end

	args._shared_ref_names = args._shared_ref_names or {}
	args._shared_ref_can_reuse = args._shared_ref_can_reuse or {}
	local ref_key = m._canonical_ref_value(ref)
	local ref_name = args._shared_ref_names[ref_key]
	if ref_name ~= nil then
		if args._shared_ref_can_reuse[ref_key] == true then
			return m._named_raw_ref_reuse_wt(ref_name)
		end
		return m_ref._get_ref(frame, args, ref)
	end

	ref_name = m._shared_ref_name(ref_key)
	args._shared_ref_names[ref_key] = ref_name

	-- Plain string refs are character notes. Generate the first occurrence as a
	-- named ref directly so exact repeated note text, such as "Sitter in the
	-- White Tower", definitely shares one reference number across the table.
	if type(ref) == "string" then
		args._shared_ref_can_reuse[ref_key] = true
		return m._named_raw_ref_wt(ref_name, ref)
	end

	-- Non-string refs continue to use Module:Ref so book/chapter formatting is
	-- preserved. If Module:Ref returns literal ref tags, name them too; if it
	-- returns an opaque strip marker, keep the original output rather than risk
	-- changing citation formatting.
	local ref_wt = m_ref._get_ref(frame, args, ref)
	local named_ref_wt, can_reuse = m._first_named_ref_wt(ref_wt, ref_name)
	args._shared_ref_can_reuse[ref_key] = can_reuse
	return named_ref_wt
end

function m._refs_wt(frame, args, refs)
	if args.suppress_refs == true then return "" end
	if refs == nil then return (m_utils._is_false_ex(args.suppress_verify) and "{{verify}}" or "") end
	local refs_wt = nil
	local refs_processed = {}
	for ref_index, ref in ipairs(type(refs) == "table" and refs or {refs}) do
		if refs_wt == nil then refs_wt = {} end
		local add = true
		for _, refp in ipairs(refs_processed) do
			if m_utils._compare2(ref, refp) == 0 then
				add = false
				break
			end
		end
		if add then
			table.insert(refs_processed, ref)
			table.insert(refs_wt, m._ref_wt(frame, args, ref))
		end
	end
	if refs_wt == nil then return (m_utils._is_false_ex(args.suppress_verify) and "{{verify}}" or "") end
	return table.concat(refs_wt, "")
end


local CURRENT_YEAR_NE = 1000
local DEATH_MARKER = "&#8224;"

function m._date_year(date)
	if type(date) ~= "table" then return nil end
	return date.year
end

function m._date_calendar(character, date)
	if type(date) ~= "table" then return nil end
	return date.calendar or character.calendar
end

function m._format_year_link(frame, args, character, date)
	local year = m._date_year(date)
	if year == nil then return nil end
	local calendar = m._date_calendar(character, date)
	local label = tostring(year)..(calendar and " "..calendar or "")
	return "[["..label.."]]"..m._refs_wt(frame, args, date.refs)
end

function m._format_year_bound_link(frame, args, character, date, attr_name)
	local year = m._date_bound_value(frame, args, date, attr_name)
	if year == nil then return nil end
	local calendar = m._date_calendar(character, date)
	local label = tostring(year)..(calendar and " "..calendar or "")
	return "[["..label.."]]"..m._refs_wt(frame, args, m._date_bound_refs(frame, args, date, attr_name))
end

function m._format_birth_year_link(frame, args, character, date)
	local exact = m._format_year_link(frame, args, character, date)
	if exact ~= nil then return exact end
	if type(date) ~= "table" then return nil end

	local lower = m._format_year_bound_link(frame, args, character, date, "lower_limit")
	local upper = m._format_year_bound_link(frame, args, character, date, "upper_limit")
	local root_refs = date.refs and m._refs_wt(frame, args, date.refs) or ""

	if lower ~= nil and upper ~= nil then
		local lower_year = m._date_bound_value(frame, args, date, "lower_limit")
		local upper_year = m._date_bound_value(frame, args, date, "upper_limit")
		if lower_year ~= nil and upper_year ~= nil and lower_year == upper_year then
			return lower..root_refs
		end
		return lower.."-"..upper..root_refs
	elseif lower ~= nil then
		return "&ge;"..lower..root_refs
	elseif upper ~= nil then
		return "&le;"..upper..root_refs
	end
	return nil
end

function m._living_status(frame, args, character)
	local val = m._get_scalar_or_epon_table_attr(frame, args, character, "alive", false)
	local refs = m._get_scalar_or_epon_table_attr_refs(frame, args, character, "alive")
	if val == nil and type(character.status) == "table" and character.status.alive ~= nil then
		val = character.status.alive
		refs = character.status.refs
	end
	return val, refs
end

function m._append_refs(dest, refs)
	if refs == nil then return dest end
	if dest == nil then dest = {} end
	for _, ref in ipairs(type(refs) == "table" and refs or {refs}) do
		table.insert(dest, ref)
	end
	return dest
end

function m._date_bound_value(frame, args, date, attr_name)
	local val = m._get_scalar_or_epon_table_attr(frame, args, date, attr_name, true)
	if type(val) == "number" then return val end
	if type(val) == "string" then return tonumber(val) end
	return nil
end

function m._date_bound_refs(frame, args, date, attr_name)
	return m._get_scalar_or_epon_table_attr_refs(frame, args, date, attr_name)
end

function m._computed_age(frame, args, character)
	local birth = character and character.birth_year or nil
	if type(birth) ~= "table" then return nil, nil, nil end

	local birth_year = m._date_year(birth)
	local birth_lower = m._date_bound_value(frame, args, birth, "lower_limit")
	local birth_upper = m._date_bound_value(frame, args, birth, "upper_limit")
	if birth_year == nil and birth_lower == nil and birth_upper == nil then return nil, nil, nil end

	local birth_calendar = m._date_calendar(character, birth)
	local target_year = nil
	local target_calendar = nil
	local target_refs = nil
	local explicit_as_of = false

	-- Optional explicit age target, used when a character's status/death date is
	-- unknown or when a source establishes a minimum/maximum age as of a
	-- specific year.  Example: birth_year.age_as_of = { calendar = "NE", year = 979 }.
	if type(birth.age_as_of) == "table" then
		target_year = m._date_year(birth.age_as_of)
		target_calendar = m._date_calendar(character, birth.age_as_of)
		target_refs = birth.age_as_of.refs
		explicit_as_of = target_year ~= nil
	end

	if target_year == nil then
		local alive_val, alive_refs = m._living_status(frame, args, character)
		if m_utils._is_true_ex(alive_val) then
			-- Living ages are calculated against the current table year, 1000 NE.
			target_year = CURRENT_YEAR_NE
			target_calendar = "NE"
			target_refs = alive_refs
		elseif m_utils._is_false_ex(alive_val) then
			-- Dead ages require a confirmed death year unless birth_year.age_as_of
			-- supplied an explicit age target above. Do not infer from deprecated explicit age overrides.
			local death_year = m._date_year(character.died_year)
			if death_year == nil then return nil, nil, nil end
			target_year = death_year
			target_calendar = m._date_calendar(character, character.died_year)
			target_refs = m._append_refs(target_refs, character.died_year and character.died_year.refs)
			target_refs = m._append_refs(target_refs, alive_refs)
		else
			return nil, nil, nil
		end
	end

	if birth_calendar ~= nil and target_calendar ~= nil and birth_calendar ~= target_calendar then return nil, nil, nil end

	local refs = nil
	refs = m._append_refs(refs, birth.refs)
	refs = m._append_refs(refs, m._date_bound_refs(frame, args, birth, "lower_limit"))
	refs = m._append_refs(refs, m._date_bound_refs(frame, args, birth, "upper_limit"))
	refs = m._append_refs(refs, target_refs)

	local meta = nil
	if explicit_as_of == true and not (target_calendar == "NE" and target_year == CURRENT_YEAR_NE) then
		meta = { as_of = { calendar = target_calendar, year = target_year } }
	end

	if birth_year ~= nil then
		return target_year - birth_year, refs, meta
	end

	-- Birth-year bounds are inverted when expressed as age: a later possible
	-- birth year gives the lower age, while an earlier possible birth year gives
	-- the upper age.
	local age_lower = birth_upper ~= nil and (target_year - birth_upper) or nil
	local age_upper = birth_lower ~= nil and (target_year - birth_lower) or nil
	if age_lower ~= nil and age_upper ~= nil then
		if age_lower > age_upper then
			local tmp = age_lower
			age_lower = age_upper
			age_upper = tmp
		end
		if age_lower == age_upper then return age_lower, refs, meta end
		return tostring(age_lower).."-"..tostring(age_upper), refs, meta
	elseif age_lower ~= nil then
		return tostring(age_lower).."+", refs, meta
	elseif age_upper ~= nil then
		return "&le;"..tostring(age_upper), refs, meta
	else
		return nil, nil, nil
	end
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
		attributes = nil,
		bonds = nil
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
	if args.bonds then
		nargs.bonds = m_utils._is_true_ex(args.bonds)
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
	attributes = args.attributes or args.columns
	if attributes == "all" then
		attributes = "Name;Sex;Era;Homeland;Born;Died;Age;Darkfriend;Shadow Controllers;Channel;Strength;Aes Sedai;WT Schism;Ajah;Spark;Wilder;Bonds;AS Years;Accepted Years;Novice Years;Age Enrolled;Traits;Notes"
	elseif attributes == "ajah" then
		attributes = "Name;Homeland;Born;Died;Age;WT Schism;Strength;AS Years;Accepted Years;Novice Years;Age Enrolled;Darkfriend;Shadow Controllers;Traits;Bonds"
		-- attributes = "Name;Homeland;Alive;Age;Died;Born;WT Schism;Ajah;Strength;Spark;Wilder;AS Years;Accepted Years;Novice Years;Age Enrolled;Shadow Controllers;Traits;Bonds"
	end
	nargs.attributes = m_utils._parse_attribute_labels(frame, args, attributes or "Name;Sex;Era;Homeland;Born;Died;Age;Darkfriend;Shadow Controllers;Channel;Strength;Aes Sedai;WT Schism;Ajah;Spark;Wilder;Bonds;AS Years;Accepted Years;Novice Years;Age Enrolled;Traits", nil)
	mw.log("Attributes: "..(nargs.attributes and m_utils._serialize(nargs.attributes, "nargs.attributes") or "nil"))
	return nargs
end

function m._fill_character(frame, args, name, character)
	-- TODO add age_enrolled_novice logic (test against / fill other dates/ages)
	local char = m_utils._json_to_table(character)
	if char.name == nil then char.name = name end
	-- mw.log("Checking ajahs: "..(char and m_utils._serialize(char, "char") or "").." - "..(char.ajahs and m_utils._serialize(char.ajahs, "ajahs") or "").." - "..(character.ajah and m_utils._serialize(character.ajah, "ajah") or "").." - "..(character.ajah and character.ajah.ajah or ""))
	if m._get_scalar_or_epon_table_attr(frame, args, character, "aes_sedai_years", false) ~= nil then
		m._fill_character_attr(frame, args, char, "aes_sedai", character, "aes_sedai_years", true)
	end
	if character.died_year then
		if character.last_year then
			mw.log("WARNING: Character "..char.name.." has both died_year and last_year attributes. Ignoring last_year.")
			char.last_year = nil
		end
		if character.alive then
			mw.log("WARNING: Character "..char.name.." has both died_year and alive attributes. Ignoring alive.")
			char.alive = false
		end
		m._fill_character_attr(frame, args, char, "last_year", character, "died_year", nil)
	end
	-- Age is now rendered from explicit birth/death dates.
	-- Do not infer birth_year, last_year, or died_year from deprecated explicit age overrides here.
	if m._get_scalar_or_epon_table_attr(frame, args, char, "accepted_years", true) ~= nil then
		m._fill_character_attr(frame, args, char, "white_tower", character, "accepted_years", true)
	end
	if m._get_scalar_or_epon_table_attr(frame, args, char, "novice_years", true) ~= nil then
		m._fill_character_attr(frame, args, char, "white_tower", character, "novice_years", true)
	end
	if m._get_scalar_or_epon_table_attr(frame, args, char, "aes_sedai_years", true) ~= nil then
		m._fill_character_attr(frame, args, char, "aes_sedai", character, "aes_sedai_years", true)
	end
	if m_utils._is_true_ex(m._get_scalar_or_epon_table_attr(frame, args, char, "aes_sedai", false)) then
		m._fill_character_attr(frame, args, char, "channeler", character, "aes_sedai", true)
		-- DO NOT fill in White Tower (account for AoL Aes Sedai and Seanchan archipelago Aes Sedai)
	end
	if char.ajah ~= nil then
		if type(char.ajah) ~= "table" then char.ajah = { ajah = char.ajah } end
		if char.ajahs == nil then char.ajahs = {} end
		table.insert(char.ajahs, char.ajah)
		m._fill_character_attr(frame, args, char, "aes_sedai", character, "ajah", true)
		m._fill_character_attr(frame, args, char, "channeler", character, "ajah", true)
		-- Yes, there were non-WT ajahs that predated the white tower, but we don't have specfics on them, so they
		-- don't matter.
		m._fill_character_attr(frame, args, char, "white_tower", character, "ajah", true)
	end
	-- mw.log("Checking "..m_utils._serialize(char, "char"))
	if (m_utils._is_true_ex(m._get_scalar_or_epon_table_attr(frame, args, char, "darkfriend", false))) and
		(m_utils._is_true_ex(m._get_scalar_or_epon_table_attr(frame, args, char, "aes_sedai", false))) then
		if char.ajahs == nil then char.ajahs = {} end
		table.insert(char.ajahs, { ajah = "Black", refs = m._get_scalar_or_epon_table_attr_refs(frame, args, char, "darkfriend") })
		as_refs = m._get_scalar_or_epon_table_attr_refs(frame, args, character, "aes_sedai")
		if as_refs then
			char.ajahs[#char.ajahs].refs = char.ajahs[#char.ajahs].refs or {}
			for _, ref in ipairs(as_refs) do table.insert(char.ajahs[#char.ajahs].refs, ref) end
		end
		if char.black_ajah == nil then char.black_ajah = { black_ajah = true, refs = char.ajahs[#char.ajahs].refs } end
	end
	local black_ajah = m._get_scalar_or_epon_table_attr(frame, args, char, "black_ajah", false)
	if black_ajah and not m_utils._is_false_ex(black_ajah) then
		m._fill_character_attr(frame, args, char, "aes_sedai", character, "black_ajah", true)
		m._fill_character_attr(frame, args, char, "channeler", character, "black_ajah", true)
		m._fill_character_attr(frame, args, char, "white_tower", character, "black_ajah", true)
	end
	if m_utils._is_true_ex(m._get_scalar_or_epon_table_attr(frame, args, char, "black_ajah", false)) then
		m._fill_character_attr(frame, args, char, "darkfriend", character, "black_ajah", true)
	end
	if m_utils._is_true_ex(m._get_scalar_or_epon_table_attr(frame, args, char, "spark", false)) then
		m._fill_character_attr(frame, args, char, "channeler", character, "spark", true)
	end
	if m_utils._is_true_ex(m._get_scalar_or_epon_table_attr(frame, args, char, "wilder", false)) then
		m._fill_character_attr(frame, args, char, "channeler", character, "wilder", true)
		m._fill_character_attr(frame, args, char, "spark", character, "wilder", true)
	end
	if m_utils._is_true_ex(m._get_scalar_or_epon_table_attr(frame, args, char, "white_tower", false)) then
		m._fill_character_attr(frame, args, char, "aes_sedai", character, "white_tower", true)
		m._fill_character_attr(frame, args, char, "channeler", character, "white_tower", true)
		m._fill_character_attr(frame, args, char, "female", character, "white_tower", true)
		m._fill_character_attr(frame, args, char, "male", character, "white_tower", false)
	end
	return char
end

function m._fill_character_attr_refs(frame, args, char, attr_name, base_char, base_attr_name)
	char[attr_name].refs = char[attr_name].refs or {}
	for _, ref in ipairs(m._get_scalar_or_epon_table_attr_refs(frame, args, base_char, base_attr_name) or {}) do
		add = true
		for _, existing_ref in ipairs(char[attr_name].refs) do
			if m_utils._compare2(ref, existing_ref) == 0 then
				add = false
				break
			end
		end
		if add then table.insert(char[attr_name].refs, ref) end
	end
end

function m._fill_character_attr(frame, args, char, attr_name, base_char, base_attr_name, val)
	if char[attr_name] == nil or char[attr_name] == val then
		char[attr_name] = { [attr_name] = val and val or (base_char[base_attr_name] and base_char[base_attr_name]), refs = m._get_scalar_or_epon_table_attr_refs(frame, args, base_char, base_attr_name) }
	elseif type(char[attr_name]) == "table" then
		if char[attr_name][attr_name] == nil then
			char[attr_name][attr_name] = val and val or (base_char[base_attr_name] and base_char[base_attr_name])
			m._fill_character_attr_refs(frame, args, char, attr_name, base_char, base_attr_name)
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
			local bonds = m._get_bond_count(character)
			local match_ajah = cargs.ajah == nil
			if cargs.ajah ~= nil then
				for _, ajah in ipairs(m._get_scalar_or_epon_table_attr(frame, args, character, "ajahs", false) or {}) do
					if string.lower(type(ajah) == "table" and ajah.ajah or ajah) == string.lower(cargs.ajah) then
						match_ajah = true
						break
					end
				end
			end
			-- TODO properly handle when argument is not provided, but is false
			if ((cargs.channelers == nil or (cargs.channelers == m._get_scalar_or_epon_table_attr(frame, args, character, "channeler", false))) and
				(cargs.ajah == nil or match_ajah == true) and
				(cargs.black_ajah == nil or (cargs.black_ajah == m._get_scalar_or_epon_table_attr(frame, args, character, "black_ajah", false))) and
				(cargs.bonds == nil or (cargs.bonds == (bonds > 0))) and
				(cargs.darkfriend == nil or (cargs.darkfriend  == m._get_scalar_or_epon_table_attr(frame, args, character, "darkfriend", false))) and
				(cargs.sparkers == nil or (cargs.sparkers == m._get_scalar_or_epon_table_attr(frame, args, character, "spark", false))) and
				(cargs.white_tower == nil or (cargs.white_tower == m._get_scalar_or_epon_table_attr(frame, args, character, "white_tower", false))) and
				(cargs.wilders == nil or (cargs.wilders == m._get_scalar_or_epon_table_attr(frame, args, character, "wilder", false)))
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
					if type(v) == "table" then
						m._get_table_structure(frame, args, s[key][1], v)
					elseif s[key][1] == nil then
						s[key][1] = type(val)
					elseif type(s[key][1]) == "string" then
						types = m_utils._split(s[key][1], ";")
						type_exists = false
						for _, t in ipairs(types) do if t == type(val) then type_exists = true break end end
						if not type_exists then
							table.insert(types, type(val))
							table.sort(types)
						end
						s[key][1] = table.concat(types, ";")
					else
						mw.log("WARNING: Unexpected structure at key "..key..". Skipping: "..tostring(s[key]))
					end
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
		else
			mw.log("WARNING: Unexpected structure at key "..key..". Skipping: "..tostring(s[key]))
		end
	end
end

-- Get the structure of the JSON file is_as it currently exists
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

-- epon = eponymous, meaning the attribute is stored is_as a scalar of the same name within the table
-- Example scalar attribute: { "my_attr": true }
-- Example epon table attribute: { "my_attr": { "my_attr": true, "refs": [...] } }
function m._get_scalar_or_epon_table_attr(frame, args, entity, attr_name, nil_tables)
	local ret
	if type(entity) ~= "table" then return nil end
	if entity[attr_name] == nil then return nil end
	if type(entity[attr_name]) ~= "table" then
		ret = entity[attr_name]
	elseif entity[attr_name][attr_name] ~= nil then
		ret = entity[attr_name][attr_name]
	else
		ret = entity[attr_name]
	end
	if type(ret) == "table" and nil_tables == true then
		ret = nil
	end
	return ret
end

function m._get_scalar_or_epon_table_attr_refs(frame, args, entity, attr_name)
	if entity[attr_name] == nil then return nil end
	if type(entity[attr_name]) ~= "table" then return nil end
	return entity[attr_name]["refs"]
end


function m._is_red_ajah(frame, args, character)
	for _, ajah in ipairs(m._get_scalar_or_epon_table_attr(frame, args, character, "ajahs", false) or {}) do
		local a = type(ajah) == "table" and ajah.ajah or ajah
		if type(a) == "string" and string.lower(a) == "red" then return true end
	end
	return false
end

function m._bonded_is_explicit_none(character)
	local bonded = character and character.bonded or nil
	if bonded == false or bonded == 0 then return true end
	if type(bonded) == "string" then
		local normalized = string.lower((bonded:gsub("^%s*(.-)%s*$", "%1")))
		if normalized == "none" then return true end
	end
	if type(bonded) == "table" then
		-- Treat an explicitly empty bonded table/array as known zero bonds.
		for _ in pairs(bonded) do return false end
		return true
	end
	return false
end

function m._has_known_no_bonds(frame, args, character)
	if m._get_bond_count(character) > 0 then return false end
	if m._bonded_is_explicit_none(character) then return true end
	-- Red sisters are inferred to have no bonds unless the JSON manually
	-- overrides that inference with a non-false/non-zero bonded value.
	return character and character.bonded == nil and m._is_red_ajah(frame, args, character)
end

function m._get_bond_entries(character)
	local bonded = character and character.bonded or nil
	if bonded == nil or bonded == false then return {} end
	if type(bonded) ~= "table" then
		if type(bonded) == "number" and bonded > 0 then return { { count = bonded } } end
		return {}
	end
	if bonded.name ~= nil or bonded.count ~= nil or bonded.notes ~= nil then return { bonded } end
	return bonded
end

function m._get_bond_count(character)
	local count = 0
	for _, bond in ipairs(m._get_bond_entries(character)) do
		if type(bond) == "number" then
			count = count + bond
		elseif type(bond) == "table" then
			if bond.name ~= nil and bond.name ~= "" then count = count + 1 end
			local n = tonumber(bond.count)
			if n ~= nil then
				count = count + n
			elseif (bond.name == nil or bond.name == "") and bond.notes ~= nil then
				count = count + 1
			end
		end
	end
	return count
end

function m._bond_notes_wt(frame, args, bond)
	local notes = {}
	if type(bond.notes) == "table" then
		for _, note in ipairs(bond.notes) do table.insert(notes, tostring(note)) end
	elseif type(bond.notes) == "string" and bond.notes ~= "" then
		table.insert(notes, bond.notes)
	end
	return #notes > 0 and " ("..table.concat(notes, "; ")..")" or ""
end

function m._anonymous_bond_wt(frame, args, rargs, bond)
	local count = tonumber(type(bond) == "table" and bond.count or bond) or 1
	local details = {}
	if type(bond) == "table" then
		if type(bond.notes) == "table" then
			for _, note in ipairs(bond.notes) do table.insert(details, tostring(note)) end
		elseif type(bond.notes) == "string" and bond.notes ~= "" then
			table.insert(details, bond.notes)
		end
		if bond.approx ~= nil then
			if bond.approx == "at least" then
				table.insert(details, "at least "..tostring(count))
			else
				table.insert(details, tostring(bond.approx).." "..tostring(count))
			end
		end
	end
	local suffix = ""
	if not (type(bond) == "table" and bond.approx ~= nil) and count ~= 1 then
		suffix = "x"..tostring(count)
	end
	return "(anon"..(#details > 0 and "; "..table.concat(details, "; ") or "")..")"..suffix..
		(type(bond) == "table" and m._refs_wt(frame, args, bond.refs) or "")
end

function m._bond_count_wt(frame, args, rargs, bond)
	return m._anonymous_bond_wt(frame, args, rargs, bond)
end

function m._bonds_wt(frame, args, rargs, character)
	local parts = {}
	for _, bond in ipairs(m._get_bond_entries(character)) do
		if bond == nil then
			mw.log("WARNING: nil bond found for character "..character.name..". Skipping.")
		elseif type(bond) == "number" then
			table.insert(parts, m._bond_count_wt(frame, args, rargs, bond))
		elseif type(bond) ~= "table" then
			mw.log("WARNING: unsupported bond value found for character "..character.name..": "..tostring(bond)..". Skipping.")
		elseif bond.name ~= nil and bond.name ~= "" then
			table.insert(parts,
				"[["..bond.name.."]]"..
				m._bond_notes_wt(frame, args, bond)..
				m._refs_wt(frame, args, bond.refs))
		elseif bond.count ~= nil then
			table.insert(parts, m._bond_count_wt(frame, args, rargs, bond))
		elseif bond.notes ~= nil then
			table.insert(parts, m._anonymous_bond_wt(frame, args, rargs, bond))
		end
	end
	local rendered = table.concat(parts, "<br />\n")
	if rendered == "" and m._has_known_no_bonds(frame, args, character) then return "None" end
	return rendered
end

function m._get_ops(frame, args, val)
	if val < 7 then return "++"..val end
	if val < 19 then return tostring(val - 6).."(+"..tostring(19 - val)..")" end
	if val < 79 then return tostring(val - 6).."("..tostring(val - 18)..")" end
	return m_utils._error(frame, "Invalid OPS value: "..tostring(val))
end

function m._get_ops_link(frame, args, val)
	return "[[Strength in the One Power rankings#rank"..val.."|"..m._get_ops(frame, args, val).."]]"
end


function m._strength_bound_value(entry, attr_name)
	if type(entry) ~= "table" then return nil end
	local bound = entry[attr_name]
	if type(bound) == "table" then bound = bound[attr_name] end
	if type(bound) == "number" then return bound end
	if type(bound) == "string" then return tonumber(bound) end
	return nil
end

function m._strength_bound_refs(entry, attr_name)
	if type(entry) ~= "table" or type(entry[attr_name]) ~= "table" then return nil end
	return entry[attr_name].refs
end

function m._strength_entry_wt(frame, args, entry)
	if type(entry) == "number" then
		return m._get_ops_link(frame, args, entry)
	end
	if type(entry) ~= "table" then return nil end
	if type(entry.strength_78) == "number" then
		return m._get_ops_link(frame, args, entry.strength_78)..m._refs_wt(frame, args, entry.refs)
	end

	local lower = m._strength_bound_value(entry, "lower_limit")
	local upper = m._strength_bound_value(entry, "upper_limit")
	local lower_refs = m._strength_bound_refs(entry, "lower_limit")
	local upper_refs = m._strength_bound_refs(entry, "upper_limit")
	local root_refs = entry.refs

	if lower ~= nil and upper ~= nil then
		if lower == upper then
			local refs = nil
			refs = m._append_refs(refs, lower_refs)
			refs = m._append_refs(refs, upper_refs)
			refs = m._append_refs(refs, root_refs)
			return m._get_ops_link(frame, args, lower)..m._refs_wt(frame, args, refs)
		end
		return m._get_ops_link(frame, args, lower)..m._refs_wt(frame, args, lower_refs).."-"..
			m._get_ops_link(frame, args, upper)..m._refs_wt(frame, args, upper_refs)..
			m._refs_wt(frame, args, root_refs)
	elseif lower ~= nil then
		local refs = nil
		refs = m._append_refs(refs, lower_refs)
		refs = m._append_refs(refs, root_refs)
		return "&ge;"..m._get_ops_link(frame, args, lower)..m._refs_wt(frame, args, refs)
	elseif upper ~= nil then
		local refs = nil
		refs = m._append_refs(refs, upper_refs)
		refs = m._append_refs(refs, root_refs)
		return "&le;"..m._get_ops_link(frame, args, upper)..m._refs_wt(frame, args, refs)
	end
	return nil
end

function m._strength_entries(strength)
	if strength == nil then return {} end
	if type(strength) ~= "table" then return { strength } end
	if strength.strength_78 ~= nil or strength.lower_limit ~= nil or strength.upper_limit ~= nil then
		return { strength }
	end
	return strength
end

function m._character_entry_wt(frame, args, cargs, rargs, character, key)
	attrs_needed = {}
	for a_i, attr in ipairs(cargs.attributes or {}) do
		attrs_needed[attr.name] = true
		for _, attr in ipairs(attr.depends or {}) do
			attrs_needed[attr] = true
		end
	end
	attrs = {}
	anchored = false
	page = m_ds._get_entity_page(frame, args, character, key)
	local aes_sedai = m._get_scalar_or_epon_table_attr(frame, args, character, "aes_sedai", false)
	local confirmed_aes_sedai = aes_sedai ~= nil and m_utils._is_true_ex(aes_sedai)
	local spark = m._get_scalar_or_epon_table_attr(frame, args, character, "spark", false)
	local wilder = m._get_scalar_or_epon_table_attr(frame, args, character, "wilder", false)
	local notes = type(character.notes) == "table" and character.notes or {character.notes}
	local wts = {}
	if attrs_needed["Spark"] == true then
		wts["Spark"] = ((m_utils._is_true_ex(spark) and "[[Spark"..(rargs.terse == true and "|🎆" or "").."]]") or
			((rargs.is_table == true) and m_utils._is_false_ex(spark) and "🙎") or "")..
			m._refs_wt(frame, args, m._get_scalar_or_epon_table_attr_refs(frame, args, character, "spark"))
	end
	if attrs_needed["Wilder"] == true then
		wts["Wilder"] = wilder ~= nil and ((m_utils._is_true_ex(wilder) and "[[Wilder"..(rargs.terse == true and "|🧠" or "").."]]") or
			((rargs.is_table == true) and m_utils._is_false_ex(wilder) and "[[White Tower|🏫]]") or "")..
			m._refs_wt(frame, args, m._get_scalar_or_epon_table_attr_refs(frame, args, character, "wilder")) or ""
	end
	for a_i, attr in ipairs(cargs.attributes or {}) do
		wt = ""
		local root_val = nil
		if attr.name == "Accepted Years" then
			root_val = character.accepted_years
			local val = m._get_scalar_or_epon_table_attr(frame, args, character, "accepted_years", true)
			wt = val and ("[[Accepted|"..(rargs.terse == true and val or val.." Accepted years").."]]"..
				m._refs_wt(frame, args, m._get_scalar_or_epon_table_attr_refs(frame, args, character, "accepted_years"))) or ""
		elseif attr.name == "Aes Sedai" then
			wt = aes_sedai ~= nil and
					(confirmed_aes_sedai and "[[Aes Sedai|"..(rargs.terse == true and "☯️" or "Aes Sedai").."]]") or
					(rargs.is_table == true and m_utils._is_false_ex(aes_sedai) and "[[Aes Sedai|❌]]" or "")..
					m._refs_wt(frame, args, m._get_scalar_or_epon_table_attr_refs(frame, args, character, "aes_sedai"))
				or ""
		elseif attr.name == "AS Years" then
			root_val = character.aes_sedai_years
			local val = m._get_scalar_or_epon_table_attr(frame, args, character, "aes_sedai_years", true)
			wt = val ~= nil and
					("[[Aes Sedai|"..val..(rargs.terse == true and "" or " years as AS").."]]") or
					""..
					m._refs_wt(frame, args, m._get_scalar_or_epon_table_attr_refs(frame, args, character, "aes_sedai_years"))
				or ""
		elseif attr.name == "Age" then
			root_val = character.birth_year
			local val, refs, meta = m._computed_age(frame, args, character)
			if val then
				wt = tostring(val)..(rargs.terse == true and "" or " yo")
				if meta ~= nil and meta.as_of ~= nil and meta.as_of.year ~= nil then
					local label = tostring(meta.as_of.year)..(meta.as_of.calendar and " "..meta.as_of.calendar or "")
					wt = wt..(rargs.terse == true and " ([["..label.."]])" or " as of [["..label.."]]")
				end
				wt = wt..m._refs_wt(frame, args, refs)
			else
				wt = ""
			end
		elseif attr.name == "Age Enrolled" then
			local val = nil
			local refs = {}
			for _, attr_name in ipairs({ "age_enrolled", "age_enrolled_novice", "age_enrolled_soldier" }) do
				if val == nil then
					root_val = character[attr_name]
					val = m._get_scalar_or_epon_table_attr(frame, args, character, attr_name, true)
					if val ~= nil then
						for _, ref in ipairs(m._get_scalar_or_epon_table_attr_refs(frame, args, character, attr_name) or {}) do
							table.insert(refs, ref)
						end
					end
				end
			end
			wt = val and (m_utils._is_true_ex(aes_sedai) and "[[White Tower|" or "")..
				((rargs.terse == true and val or "Enrolled "..val.." yo")..
				(m_utils._is_true_ex(aes_sedai) and "]]" or "")..
				m._refs_wt(frame, args, refs)) or ""
		elseif attr.name == "Ajah" then
			parts = {}
			for _, ajah in ipairs(character.ajahs or {}) do
				if ajah == nil then
					mw.log("WARNING: nil ajah found for character "..character.name..". Skipping.")
				else
					local a = ajah
					if type(a) == "table" then a = ajah.ajah end
					-- if type(a) == "table" then return m_utils._error(frame, "Invalid ajah value for character "..character.name..": "..tostring(a)..": "..m_utils._serialize(character.ajahs, "ajahs")) end
					table.insert(parts,
						(string.lower(a) == "na" and (rargs.is_table == true and "[[Ajah|NA]]" or "") or
							("[["..a.." Ajah|"..(
								(rargs.terse == true and m_ajahs.emoji_map[string.lower(a)]) or
								a).."]]"))..
						m._refs_wt(frame, args, ajah.refs))
				end
			end
			if m._get_scalar_or_epon_table_attr(frame, args, character, "accepted", false) == true then
				table.insert(parts,
					"[[Accepted"..(rargs.terse == true and "|A" or "").."]]"..
					m._refs_wt(frame, args, m._get_scalar_or_epon_table_attr_refs(frame, args, character, "accepted")))
			end
			if m._get_scalar_or_epon_table_attr(frame, args, character, "novice", false) == true then
				table.insert(parts,
					"[[novice"..(rargs.terse == true and "|N" or "").."]]"..
					m._refs_wt(frame, args, m._get_scalar_or_epon_table_attr_refs(frame, args, character, "novice")))
			end
			wt = table.concat(parts, (rargs.is_table == true and "<br />" or ", "))
		elseif attr.name == "Alive" then
			local val = m._get_scalar_or_epon_table_attr(frame, args, character, "alive", false)
			local alive = m_utils._is_true_ex(val)
			local dead = m_utils._is_false_ex(val)
			wt = val ~= nil and (((alive or dead) and "[[:Category:"..(alive and "Living" or "Deceased").."|"..(rargs.terse == true and (alive and "🚶" or "🪦") or (alive and "Alive" or "Dead")).."]]" or val))..
				m._refs_wt(frame, args, m._get_scalar_or_epon_table_attr_refs(frame, args, character, "alive")) or ""
		elseif attr.name == "Bonds" then
			wt = m._bonds_wt(frame, args, rargs, character)
		elseif attr.name == "Born" then
			local year_wt = m._format_birth_year_link(frame, args, character, character.birth_year)
			wt = year_wt and (rargs.terse == false and "born " or "")..year_wt or ""
		elseif attr.name == "Channel" then
			if (m_utils._is_true_ex(m._get_scalar_or_epon_table_attr(frame, args, character, "channeler", false))) then
				wt = "[[Channeling"..(rargs.terse == true and "|⚡" or "").."]]"..
					m._refs_wt(frame, args,
						m._get_scalar_or_epon_table_attr_refs(frame, args, character, "channeler") or
						m._get_scalar_or_epon_table_attr_refs(frame, args, character, "spark") or
						m._get_scalar_or_epon_table_attr_refs(frame, args, character, "wilder"))
			elseif (m_utils._is_false_ex(m._get_scalar_or_epon_table_attr(frame, args, character, "channeler", false))) then
				wt = ((rargs.terse == true) and ("-"..m._refs_wt(frame, args, m._get_scalar_or_epon_table_attr_refs(frame, args, character, "channeler")))) or ""
			else
				wt = "?"
			end

		elseif attr.name == "Darkfriend" then
			local darkfriend = m._get_scalar_or_epon_table_attr(frame, args, character, "darkfriend", false)
			local badge_style = 'display:inline-block;min-width:2em;padding:0 .35em;border-radius:.25em;text-align:center;font-weight:600;line-height:1.35;'
			wt = (
				(m_utils._is_true_ex(darkfriend) and '[[Darkfriend|<span style="'..badge_style..'background:rgba(90,31,31,.35);color:#f7eeee;border:1px solid rgba(138,58,58,.75);">DF</span>]]') or
				(m_utils._is_false_ex(darkfriend) and '[[Light|<span style="'..badge_style..'background:rgba(255,242,168,.25);color:#fff2a8;border:1px solid rgba(201,174,72,.75);">LT</span>]]')
			) or ""
			if wt ~= "" then
				local refs = nil
				for _, a in ipairs({ "ajah", "darkfriend" }) do
					for _, ref in ipairs(m._get_scalar_or_epon_table_attr_refs(frame, args, character, a) or {}) do
						if refs == nil then refs = {} end
						table.insert(refs, ref)
					end
				end
				wt = wt..m._refs_wt(frame, args, refs)
			end
		elseif attr.name == "Died" then
			-- Combined visible status/date column:
			-- N/A = living/dead status not applicable to main-continuity tracking,
			-- blank = alive, dagger = dead, dagger + date = dead with known year, ? = unknown.
			local died_applicable = m._get_scalar_or_epon_table_attr(frame, args, character, "died_applicable", false)
			local died_applicable_refs = m._get_scalar_or_epon_table_attr_refs(frame, args, character, "died_applicable")
			local alive_val, alive_refs = m._living_status(frame, args, character)
			local death_year_wt = m._format_year_link(frame, args, character, character.died_year)
			if m_utils._is_false_ex(died_applicable) then
				wt = "N/A"..m._refs_wt(frame, args, died_applicable_refs)
			elseif death_year_wt then
				wt = DEATH_MARKER.." "..death_year_wt
			elseif m_utils._is_false_ex(alive_val) then
				wt = DEATH_MARKER..m._refs_wt(frame, args, alive_refs)
			elseif m_utils._is_true_ex(alive_val) then
				wt = ""
			else
				wt = "?"
			end
		elseif attr.name == "Era" then
			wt = character.calendar and "[["..character.calendar.."]]" or ""
		elseif attr.name == "Homeland" then
			local origin = m._get_scalar_or_epon_table_attr(frame, args, character, "origin", false)
			if origin then
				wt = (m_places._get_place_link_wt(frame, args, origin, true) or origin)..
					m._refs_wt(frame, args, m._get_scalar_or_epon_table_attr_refs(frame, args, character, "origin"))
			end
		elseif attr.name == "Name" then
			local ns = {}
			if rargs.is_table == true and not m_utils._is_false_ex(args.suppress_notes_footnotes) then
				for _, note in ipairs(notes) do if note ~= nil and note ~= "" then
					table.insert(ns, m._refs_wt(frame, args, note)) end
				end
			end
			wt = "[["..page.."]]"..table.concat(ns, "")
		elseif attr.name == "Novice Years" then
			root_val = character.novice_years
			local val = m._get_scalar_or_epon_table_attr(frame, args, character, "novice_years", true)
			wt = val and ("[[Novice|"..(rargs.terse == true and val or val.." novice years").."]]"..
				m._refs_wt(frame, args, m._get_scalar_or_epon_table_attr_refs(frame, args, character, "novice_years"))) or ""
		elseif attr.name == "Sex" then
			local male = m._get_scalar_or_epon_table_attr(frame, args, character, "male", false)
			local female = m._get_scalar_or_epon_table_attr(frame, args, character, "female", false)
			parts = {}
			if male == true then
				table.insert(parts, "[[:Category:Men|"..(rargs.terse == true and "M" or "Male").."]]"..
					m._refs_wt(frame, args, m._get_scalar_or_epon_table_attr_refs(frame, args, character, "male")))
			end
			if female == true then
				table.insert(parts, "[[:Category:Women|"..(rargs.terse == true and "F" or "Female").."]]"..
					m._refs_wt(frame, args, m._get_scalar_or_epon_table_attr_refs(frame, args, character, "female")))
			end
			if (male ~= true and male ~= false and female ~= true and female ~= false) and
				(string.lower(male) == "na" or string.lower(female) == "na")
			then
				refs = {}
				for _, k in ipairs({ "male", "female" }) do
					for _, r in ipairs(m._refs_wt(frame, args, m._get_scalar_or_epon_table_attr_refs(frame, args, character, k))) do
						table.insert(refs, r)
					end
				end
				table.insert(parts, (rargs.terse == true and "NA"..table.concat(refs, "") or ""))
			end
			wt = table.concat(parts, (rargs.is_table == true and "<br />" or ", "))
		elseif attr.name == "Shadow Controllers" then
			scs = {}
			for _, sc in ipairs(character.shadow_controllers or {}) do
				if sc == nil then
					mw.log("WARNING: nil shadow controller found for character "..character.name..". Skipping.")
				else
					if type(sc) == "table" then
						if sc.name == nil or sc.name == "" then
							mw.log("WARNING: shadow controller with nil or empty name found for character "..character.name..". Skipping.")
						else
							table.insert(scs, "[["..sc.name.."]]"..m._refs_wt(frame, args, sc.refs))
						end
					else
						table.insert(scs, "[["..sc.."]]")
					end
				end
			end
			wt = (#scs > 0) and table.concat(scs, rargs.is_table == true and "<br />" or ", ") or ""
		elseif attr.name == "Spark" then
			wt = wts["Spark"]
		elseif attr.name == "Strength" then
			local vals = {}
			local val = m._get_scalar_or_epon_table_attr(frame, args, character, "strength_78", false)
			for _, v in ipairs(m._strength_entries(val)) do
				local rendered = m._strength_entry_wt(frame, args, v)
				if rendered == nil then
					mw.log("WARNING: Unsupported strength_78 value found for character "..character.name..". Ignoring.")
				else
					table.insert(vals, rendered)
				end
			end
			wt = table.concat(vals, rargs.is_table == true and "<br />" or ", ") or ""
		elseif attr.name == "Traits" then
			ts = {}
			for _, t in ipairs(character.traits or {}) do
				if t == nil then
					mw.log("WARNING: nil trait found for character "..character.name..". Skipping.")
				else
					local val = t
					if t == "Liandrin's group" then
						val = "[[Liandrin's group of Black Sisters|Liandrin's group]]"
					end
					table.insert(ts, val)
				end
			end
			for _, t in ipairs({"liandrin's_group", "sworn_to_rand", "captured_at_dumais_wells"}) do
				local val = m._get_scalar_or_epon_table_attr(frame, args, character, t, false)
				if val ~= nil and m_utils._is_true_ex(val) then
					table.insert(ts, (
							(t == "liandrin's_group" and "[[Liandrin's group of Black Sisters|Liandrin's group]]") or
							(t == "sworn_to_rand" and (confirmed_aes_sedai and "[[Rand's Aes Sedai|" or "")..
								"Sworn to Rand"..
								(confirmed_aes_sedai and "]]" or "")) or
							(t == "captured_at_dumais_wells" and "Captured at [[Dumai's Wells]]") or
							"")..
						m._refs_wt(frame, args, m._get_scalar_or_epon_table_attr_refs(frame, args, character, t)))
				end
			end
			for _, t in ipairs({"Spark", "Wilder"}) do if wts[t] ~= "" then table.insert(ts, wts[t]) end end
			wt = (table.concat(ts, rargs.is_table == true and "<br />\n" or " "))..
				(rargs.is_table == true and "<br />\n" or "")..
				(m._refs_wt(frame, args, m._get_scalar_or_epon_table_attr_refs(frame, args, character, "traits")) or "") or ""
		elseif attr.name == "WT Schism" then
			local val = m._get_scalar_or_epon_table_attr(frame, args, character, "wt_schism_faction", false)
			if val ~= nil then
				local loyalist = string.lower(val) == "loyalist"
				local rebel = string.lower(val) == "rebel"
				local unaligned = string.lower(val) == "unaligned"
				local link_target = "White_Tower_Schism"..(loyalist and "#Elaida's_White_Tower" or (rebel and "#Rebel_Aes_Sedai") or (unaligned and "#Unaligned_sisters") or "")
				local link_display = rargs.terse == true and
					(loyalist and "🟥" or (rebel and "🟦") or (unaligned and "🏳️") or val) or
					val
				wt = "[["..link_target.."|"..link_display.."]]"..
					m._refs_wt(frame, args, m._get_scalar_or_epon_table_attr_refs(frame, args, character, "wt_schism_faction"))
			end
		elseif attr.name == "Wilder" then
			wt = wts["Wilder"]
		elseif attr.name == "Notes" then
			wt = character.notes and (
					table.concat(notes,
					rargs.is_table == true and "<br />\n" or " ")) or ""
			wt = ((string.len(wt) > 0 and rargs.is_table == false) and "- " or "")..wt
		else
			local key = nil
			for _, c in ipairs({ attr.field, attr.name }) do if c and character[c] then key = c end end
			if key then wt = character[key]..m._refs_wt(frame, args, m._get_scalar_or_epon_table_attr_refs(frame, args, character, key)) end
		end
		if m.fields[attr.name] ~= nil and m.fields[attr.name].range == true and root_val ~= nil then
			lower = m._get_scalar_or_epon_table_attr(frame, args, root_val, "lower_limit", true)
			if lower ~= nil then lower = tostring(lower)..m._refs_wt(frame, args, m._get_scalar_or_epon_table_attr_refs(frame, args, root_val, "lower_limit")) end
			upper = m._get_scalar_or_epon_table_attr(frame, args, root_val, "upper_limit", true)
			if upper ~= nil then upper = tostring(upper)..m._refs_wt(frame, args, m._get_scalar_or_epon_table_attr_refs(frame, args, root_val, "upper_limit")) end
			p = string.len(wt) > 0
			wt = wt..((lower ~= nil or upper ~= nil) and (p and " (" or "")..
				(
					lower ~= nil and upper ~= nil and (lower.."-"..(rargs.is_table == true and "<br />\n" or "")..upper) or
					(lower ~= nil and "&gt;"..lower) or
					(upper ~= nil and "&lt;"..upper)
				)..(p and ")" or "") or "")
		end
		if (rargs.is_table == false) and wt ~= nil and (string.len(wt) > 0) and (a_i > 1) and (attr.name ~= "Notes") then
			wt = "("..wt..")"
		end
		if anchored == false then
			wt = "<span id=\""..(args.anchor_prefix or "")..page.."\">"..wt.."</span>"
			anchored = true
		end
		if (rargs.is_table == true) or (wt ~= nil and string.len(wt) > 0) then table.insert(attrs, wt) end
	end
	return table.concat(attrs, (rargs.delimiter or ""))
end

-- Useful test code:
-- =p._get_characters_ul(mw.getCurrentFrame(), { sparkers="True", wilders="True" })
function m._get_characters_ul(frame, args)
	local rendered = ""
	m._reset_ref_cache(args)
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

m.fields = {
	["Accepted Years"] = {
		vertical = true,
		link = true,
		link_target = "Accepted",
		range = true
	},
	["Aes Sedai"] = {
		vertical = true,
		link = true
	},
	["Age Enrolled"] = {
		vertical = true,
		range = true
	},
	["Ajah"] = {
		vertical = true,
		link = true
	},
	["Alive"] = {
		vertical = true,
		link = true,
		link_target = ":Category:Living"
	},
	["AS Years"] = {
		vertical = true,
		link = true,
		link_target = "Aes Sedai",
		range = true
	},
	["Bonds"] = {
		link_target = "Bonding"
	},
	["Born"] = {
		vertical = true,
		link = true,
		link_target = "Timeline"
	},
	["Channel"] = {
		vertical = true,
		link = true,
		link_target = ":Category:Channelers"
	},
	["Darkfriend"] = {
		vertical = true,
		link = true
	},
	["Died"] = {
		vertical = true,
		link = true,
		link_target = "Timeline"
	},
	["Era"] = {
		link = true,
		link_target = "Calendar"
	},
	["Novice Years"] = {
		vertical = true,
		link = true,
		link_target = "Novice",
		range = true
	},
	["Spark"] = {
		vertical = true,
		link = true
	},
	["Strength"] = {
		vertical = true,
		link = true,
		link_target = "Strength_in_the_One_Power_rankings"
	},
	["Traits"] = {
		depends = { "Spark", "Wilder" },
	},
	["Wilder"] = {
		vertical = true,
		link = true
	},
	["WT Schism"] = {
		vertical = true,
		link = true,
		link_target = "White Tower Schism"
	}
}

-- Useful test code:
-- =p._get_characters_wikitable(mw.getCurrentFrame(), { all="True", attributes="Ajah;Spark;Wilder;Homeland" })
function m._get_characters_wikitable(frame, args)
	m._reset_ref_cache(args)
	local cargs = m._copy_char_args(args)
	local keys, chars = m._get_characters(frame, args, cargs)
	headers = {}
	for _, column in ipairs(cargs.attributes or {}) do
		parms = m.fields[column.name] or { vertical = false, link = false, link_target = nil }
	-- "Name;Homeland;Traits;Notes", nil)
		table.insert(headers,
			(parms.vertical == true and "<span style=\"display:block; writing-mode:vertical-lr; transform:rotate(180deg)\">" or "")..
			(parms.link == true and ("[["..(parms.link_target and parms.link_target.."|" or "") or "") or "")..
			column.name..
			(parms.link == true and "]]" or "")..
			(parms.vertical == true and "</span>" or ""))
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