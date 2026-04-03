local m_utils = require('Module:Utils')
local m_pov_db = mw.loadJsonData('Module:Povs/povs.json')

local m = {}

m.pov_char_cnt = 0
m.pov_cnt = 0
m.all_povs_desktop_table = "{|class=\"wikitable sortable hidden\"\n".."!Num!!Pov!!Count!!Chapters"
m.all_povs_mobile_list = "<div class=\"desktop-hidden\">\n"

for _, c in ipairs(m_pov_db) do
	m.pov_char_cnt = m.pov_char_cnt + 1
    bs = ""
    mbs = ""
	pov_cnt_pre = m.pov_cnt
    for _, p in ipairs(c.povs) do
    	if string.len(bs) > 0 then bs = bs.."<br>" end
    	if string.len(mbs) > 0 then mbs = mbs..", " end
    	chs = ""
	    if p.chapters then
	    	prefixed = false
	    	chapters = p.chapters
    		for chi, ch in ipairs(chapters) do
    			m.pov_cnt = m.pov_cnt + 1
				chs = chs..", "
				subtarget = ""
				if not (ch == "Prologue" or ch == "Epilogue" or ch == "Ravens") then
					if not prefixed then chs = chs.."Chapter(s) " end
					prefixed = true
					subtarget = "Chapter "
				end
				chs = chs.."[["..p.book.."/"..subtarget..ch.."|"..ch.."]]"
			end
		else
			m.pov_cnt = m.pov_cnt + 1
    	end
    	bs = bs.."''[["..p.book.."]]''"..chs
		mbs = mbs.."''[["..p.book.."]]''"..chs
	end
    m.all_povs_desktop_table = m.all_povs_desktop_table.."\n|-\n|"..m.pov_char_cnt.."||"..string.gsub(c.pov, "/", "<br/>").."||"..(m.pov_cnt - pov_cnt_pre).."||"..bs
    m.all_povs_mobile_list = m.all_povs_mobile_list.."# "..c.pov.." ("..(m.pov_cnt - pov_cnt_pre).."): "..mbs.."\n"
end
m.all_povs_desktop_table = m.all_povs_desktop_table.."\n|}"
m.all_povs_mobile_list = m.all_povs_mobile_list.."</div>"

function m._get_number_of_pov_characters(frame, args)
	-- This isn't actually the number of POVs. Multiple POVs by the same
	-- character in a given chapter will only count as one for the purposes
	-- of this count. This is an area for improvement.
	-- Note: This is NOT a count of POV chapters. A given chapter will be
	-- counted once for each character who has a POV in it.
    return m.pov_char_cnt
end

function m._get_number_of_povs(frame, args)
    return m.pov_cnt
end

function m._render_all_povs(frame, args)
	return m.all_povs_desktop_table.."\n"..m.all_povs_mobile_list
end

function m.get_number_of_pov_characters(frame)
	local args = m_utils.get_merged_args(frame)
    local status, result = pcall(m._get_number_of_pov_characters, frame, args)
    if status then
        return result
    end
    return m_utils._error(frame,
        "get_number_of_pov_characters failed with the following input:\n"..
        m_utils._format_code(frame, m_utils._serialize(args))..
        "'''CAUSE:''' "..result.."\n")
end

function m.get_number_of_povs(frame)
	local args = m_utils.get_merged_args(frame)
    local status, result = pcall(m._get_number_of_povs, frame, args)
    if status then
        return result
    end
    return m_utils._error(frame,
        "get_number_of_povs failed with the following input:\n"..
        m_utils._format_code(frame, m_utils._serialize(args))..
        "'''CAUSE:''' "..result.."\n")
end

function m.render_all_povs(frame)
	local args = m_utils.get_merged_args(frame)
    local status, result = pcall(m._render_all_povs, frame, args)
    if status then
        return result
    end
    return m_utils._error(frame,
        "render_all_povs failed with the following input:\n"..
        m_utils._format_code(frame, m_utils._serialize(args))..
        "'''CAUSE:''' "..result.."\n")
end

return m