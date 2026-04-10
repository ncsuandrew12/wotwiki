local m_ajahs_json = mw.loadJsonData('Module:Ajahs/ajahs.json')
local m = {}

m.emoji_map = {}
for key, ajah in pairs(m_ajahs_json) do
	m.emoji_map[string.lower(key)] = ajah.emoji
end

return m