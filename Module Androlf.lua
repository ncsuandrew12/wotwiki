local m_utils = require('Module:Utils')
local m_sites_json = mw.loadJsonData('Module:Androlf/wot_sites.json')

local m = {}

-- Useful test code:
-- print(p._get_site_wikitable(mw.getCurrentFrame(), { defunct="False"}))
function m._get_site_wikitable(frame, args)
	local rendered = "{| class=\"wikitable sortable\"\n"
	rendered = rendered.."|+\n"
	rendered = rendered.."! data-sort-type=\"text\" |#\n"
	rendered = rendered.."! data-sort-type=\"text\" |Name\n"
	rendered = rendered.."! data-sort-type=\"text\" |WoT-centric\n"
	rendered = rendered.."! data-sort-type=\"text\" |TV Show\n"
	rendered = rendered.."! data-sort-type=\"text\" |Site\n"
	rendered = rendered.."! data-sort-type=\"text\" |Site Type\n"
	rendered = rendered.."! data-sort-type=\"text\" |Audience\n"
	rendered = rendered.."! class=\"unsortable\" |Notes\n"
	for site_index, site in ipairs(m_sites_json) do
		if args.defunct == nil or ((string.lower(args.defunct) == "true") == (site.defunct or false)) then
			rendered = rendered.."|-\n"
			rendered = rendered.."|"..site_index.."\n"
            -- rowspan = tostring(#site.subsites)
            rowspan = 0
			for _, subsite in ipairs(site.subsites) do
                rowspan = rowspan + 1
            end
			rendered = rendered.."| rowspan="..rowspan.." | "..site.name.."\n"
			rendered = rendered.."| rowspan="..rowspan.." | "..(site.wot_centric ~= nil and (site.wot_centric and "Yes" or "No") or "").."\n"
			rendered = rendered.."| rowspan="..rowspan.." | "..(site.tv_show ~= nil and (site.tv_show) or "").."\n"
			for subsite_i, subsite in ipairs(site.subsites) do
				if subsite_i > 1 then
					rendered = rendered.."|-\n"
				end
				stlc = string.lower(subsite.site_type or "")
				if subsite.site_url == nil or subsite.site_url == "" then
					error("Missing site_url for subsite of "..site.name)
				elseif stlc == "subreddit" then
					rendered = rendered.."| {{Subreddit|"..subsite.site_url.."}}\n"
				elseif stlc == "lemmy" then
					rendered = rendered.."| {{Link |url=https://"..(subsite.site_lemmy_server or "lemmy.world").."/c/"..subsite.site_url.." |text=c/"..subsite.site_url.."}}\n"
				elseif stlc == "website" or
						stlc == "wiki" or
						stlc == "discord" or
						stlc == "deviantart" or
						stlc == "instagram" or
						stlc == "substack" or
						stlc == "android app" or
						stlc == "ios app" or
						stlc == "tumblr" or
						stlc == "text" or
						stlc == "youtube" or
						stlc == "facebook" or
						stlc == "facebook group" or
						stlc == "facebook page" or
						stlc == "facebook group/page" or
						stlc == "podcast" or
						stlc == "blog" or
						stlc == "mud" or
						stlc == "newsgroup" or
						stlc == "steam" then
					rendered = rendered.."| {{Link |url="..subsite.site_url..((subsite.site_text ~= nil and subsite.site_text ~= "") and (" |text="..subsite.site_text) or "").."}}\n"
				else
					error("Unknown site_type: "..subsite.site_type)
				end
				rendered = rendered.."| "..subsite.site_type.."\n"
				rendered = rendered.."| "..(subsite.audience and "{{RoughPop|"..subsite.audience.."}}" or "").."\n"
                rendered = rendered.."|\n"
				if subsite.notes ~= nil then
                    for _, note in ipairs(subsite.notes) do
                        if string.len(note) > 0 then
                            rendered = rendered..note.."\n"
                        end
                    end
				end
			end
		end
	end
	rendered = rendered.."|}\n"
    return frame.preprocess(frame, rendered)
end

function m.get_site_wikitable(frame)
	return m_utils.invoke_api(frame, m._get_site_wikitable, "_get_site_wikitable")
end

return m
