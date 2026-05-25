local m = {}
m.mArguments = require('Dev:Arguments')

function m._compare(l, r, key)
    if l == nil and r == nil then return 0 end
    if l == nil then return -1 end
    if r == nil then return 1 end
    if type(l) ~= type(r) then
        error("Cannot compare "..type(l).." and "..type(r).." table")
        return nil
    end
    local cl = l
    local cr = r
    if type(l) == "table" then
        if key == nil then key = "index" end
        cl = l[key]
        cr = r[key]
        if cl == nil or cr == nil then
            error("Cannot compare nil "..key.."s")
            return nil
        end
    end
    return cl > cr and 1 or (cl == cr and 0 or -1)
end

function m._compare2(l, r)
    if l == nil and r == nil then return 0 end
    if l == nil then return 1 end
    if r == nil then return -1 end
    if type(l) ~= type(r) then return tostring(l) > tostring(r) and 1 or -1 end
    if type(l) == "table" then
        for _, set in ipairs({ { t1=l, t2=r, factor=1 }, { t1=r, t2=l, factor=-1 } }) do
            keys = {}
            for k, vl in ipairs(set.t1) do table.insert(keys, k) end
            table.sort(keys)
            for _, k in ipairs(keys) do
                c = m._compare(set.t1[k], set.t2[k])
                if c ~= 0 then return c * set.factor end
            end
        end
        return 0
    end
    return r > l and 1 or (l == r and 0 or -1)
end

function m._error(frame, msg)
    local err, _ = string.gsub(
            '<div name="Error notice" class="boilerplate metadata" id="error" style="background-color: #cc0033; margin: 0 1em; padding: 0 10px; border: 1px solid #aaa;">'..
            "'''ERROR:''' "..(msg or "No error message provided!")..'</div>\n',
            "\n", "<br />\n")
    return err
end

function m._format_code(frame, c)
    return frame:callParserFunction('#tag', { 'nowiki', frame:callParserFunction('#tag', { 'pre', c }) })
end

function m._is_true(val)
    return val == true or string.lower(tostring(val)) == "true"
end

function m._is_true_ex(val)
    vs = tostring(val)
    return m._is_true(val) or val == 1 or vs == "yes" or vs == "1"
end

function m._is_false(val)
    return val == false or string.lower(tostring(val)) == "false"
end

function m._is_false_ex(val)
    vs = tostring(val)
    return m._is_false(val) or val == 0 or vs == "no" or vs == "0"
end

function m._json_to_table(json)
    local json_type = type(json)
    local table = nil
    mw.log("_json_to_table: processing "..json_type)
    if json_type == "table" then
        table = {}
        for k, v in pairs(json) do
            mw.log("_json_to_table: processing key: "..tostring(k)..": "..type(k)..": "..(type(k) == "string" and string.sub(k, 1, 8) or ""))
            if type(k) ~= "string" or (type(k) == "string" and string.sub(k, 1, 8) ~= "_comment") then
                table[k] = m._json_to_table(v)
            else
                mw.log("_json_to_table: ignoring key: "..tostring(k))
            end
        end
    else
        table = json
    end
    return table
end

function m._parse_attribute_labels(frame, args, columns, fields)
    columns = m._split(columns, ';')
	for ci, col in ipairs(columns) do
		col_split = m._split(col, ':')
		columns[ci] = {
			name = col_split[1],
			display = col_split[2] and col_split[2] or col_split[1],
			field = fields and fields[col_split[1]] or nil
		}
	end
    return columns
end

function m._ref_dict_to_wt(frame, args, ref)
    wt = "{{ref"
    if ref.book then
        wt = wt.."/book"
    end
    for _, parm in ipairs({ "book", "chapter", "section", "chapter2", "section2", "entry", "word" }) do
        key = parm
        if key == "word" then
            key = "section"
        end
        if ref[parm] then
            wt = wt.."|"..key.."="..ref[parm]
        end
    end
    return wt.."}}"
end

function m._table_union(t, o)
    for _, ov in ipairs(o) do
        local found = false
        if t == nil then
            t = {}
        else
            for _, tv in ipairs(t) do
                if tv == ov then
                    found = true
                    break
                end
            end
        end
        if not found then table.insert(t, ov) end
    end
    return t
end

function m._map_union(t, o, handleCollision)
	for ok, ov in pairs(o) do
		local collision = false
		if t == nil then
			t = {}
		else
			for tk, tv in pairs(t) do
				if tk == ok and not (tv == ov) then
					collision = true
					break
				end
			end
		end
		if not collision or not (handleCollison == "o") then
			t[ok] = ov
		elseif not (handleCollision == "t") then
			error("Collision while merging tables. key: "..ok..", o: "..ov..", t: "..t[ok])
		end
	end
	return t
end

function m._parse_date(frame, str)
    local year, month, day = string.match(str, "^(%d+)[-/](%d+)[-/](%d+)$")
    if year and month and day then
        return os.time({ year = tonumber(year), month = tonumber(month), day = tonumber(day) })
    end
    return error("Unsupported date format: "..frame.args["date"]..". Supported formats are YYYY-MM-DD or YYYY/MM/DD.")
end

function m._select_random_entry(frame, args, table)
    local len = 0
    for _, _ in ipairs(table) do
        len = len + 1
    end
    if (table == nil or len == 0) then
        return error(
                "No entries found! "..
                    m._format_code(frame, m._serialize(args, "args")).."\n"..
                    m._format_code(frame, m._serialize(table, "table")),
                2)
    end
    local seed_str = nil
    for key, value in pairs(args) do
        if key == "random_seed" and value and string.len(value) > 0 then
            seed_str = value
        end
    end
    local seed = os.time()
    if seed_str then
        seed = tonumber(seed_str)
    end
    math.randomseed(seed)
    return table[math.random(len)]
end

function m._serialize(val, name, depth, strict, pretty, quote_name)
    depth = depth or 0
    local str = ''
    if pretty then str = string.rep("  ", depth) end
    if name then
        if quote_name then
            str = str..string.format("[%q]", name)
        elseif string.match(name, "%s") then
            m._error(nil, "Invalid non-quoted name: "..name)
        else
            str = str..name
        end
        str = str.."="
    end
    if type(val) == "table" then
        if val._wotwiki_raw then
            str = str..val._val
        else
            str = str.."{"
            if pretty then str = str.."\n" end
            local first = true
            local quote_keys = false
            for k, _ in pairs(val) do
                if string.match(k, "%s") then 
                    quote_keys = true
                    break
                end
            end
            for k, v in pairs(val) do
                local name = nil
                if (type(k) ~= "number") then name = k end
                if not first then 
                    str = str..","
                    if pretty then str = str.."\n" end
                end
                str = str..m._serialize(v, name, depth + 1, strict, pretty, quote_keys)
                first = false
            end
            if pretty then str = str.."\n"..string.rep("  ", depth) end
            str = str.."}"
        end
    elseif type(val) == "number" then
        str = str..tostring(val)
    elseif type(val) == "string" then
        str = str..string.format("%q", val)
    elseif type(val) == "boolean" then
        str = str..(val and "true" or "false")
    elseif val == nil then
        str = str.."nil"
    else
        local msg = "non-serializeable datatype: "..type(val)
        if strict then
            error(msg)
        else
            str = str.."\"["..msg.."]\""
        end
    end
    return str
end

function m._split(str, delimiter)
    local result = {}
    -- Use gmatch to find all substrings that are NOT the delimiter
    -- and capture them. The pattern '([^' .. delimiter .. ']+)' matches
    -- one or more characters that are not the delimiter.
    for entry in string.gmatch(str, '([^' .. delimiter .. ']+)') do
        table.insert(result, entry)
    end
    return result
end

function m._str_ends_punct(str)
    return string.match(str, "[\\.!?;,]$")
end

function m._table_insert_or_create(t, v)
    if v == nil then return t end
    if t == nil then t = {} end
    table.insert(t, v)
    return t
end

function m.error(frame)
    local msg = nil
    for key, value in pairs(frame.args) do
        if key == 1 or key == "msg" then
            if key == "msg" or string.len(value) > 0 then
                msg = value
            end
        end
    end
    return m._error(frame, msg)
end

function m.invoke_api(frame, api, label, arg_aliases)
	local args = m.get_merged_args(frame)
	if arg_aliases then
		for arg_name, aliases in pairs(arg_aliases) do
			for _, arg_alias in ipairs(aliases) do
				if args[arg_name] and args[arg_alias] then
					error("Argument collision: invocation specifies both "..arg_name.." and "..arg_alias)
					return nil
				elseif args[arg_name] then
					mw.log("Setting "..arg_alias.." to "..arg_name..": "..args[arg_name])
					args[arg_alias] = args[arg_name]
				elseif args[arg_alias] then
					mw.log("Setting "..arg_name.." to "..arg_alias..": "..args[arg_alias])
					args[arg_name] = args[arg_alias]
				end
			end
		end
	end
    local status, result = pcall(api, frame, args)
    if status then
        return result
    end
    return m._error(frame,
        (label == nil and "Failure" or label.." failed").." with the following input:\n"..
        m._format_code(frame, m._serialize(frame.args)).."\n"..
        m._format_code(frame, m._serialize(args)).."\n"..
        "'''CAUSE:''' "..result.."\n")
end

function m.get_merged_args(frame)
	return m._table_union(m.mArguments.getArgs(frame), frame.args, "o")
end

m.int_to_roman_numeral = {
    [0] = "0",
    [1] = "I",
    [2] = "II",
    [3] = "III",
    [4] = "IV",
    [5] = "V",
    [6] = "VI",
    [7] = "VII",
    [8] = "VIII",
    [9] = "IX",
    [10] = "X",
    [11] = "XI",
    [12] = "XII",
    [13] = "XIII",
    [14] = "XIV",
    [15] = "XV",
    [16] = "XVI",
    [17] = "XVII",
    [18] = "XVIII",
    [19] = "XIX",
    [20] = "XX",
}

return m