local m_ds = require('Module:Dataset')
local m_places_json = mw.loadJsonData('Module:Places/places.json')
local m = {}

function m._get_place(frame, args, name)
	if m.places_map[string.lower(name)] then
		return m.places_map[string.lower(name)]
	end
	for key, place in pairs(m_places_json) do
		if (place.demonym and string.lower(place.demonym) == string.lower(name)) then
			return place
		end
	end
	return nil
end

function m._get_place_link_wt(frame, args, name, terse)
	mw.log("Getting place link for: "..name)
	local link = nil
	local place = m._get_place(frame, args, name)
	if place then
		link = "[["..m_ds._get_entity_page(frame, args, place, name)
		if terse then
			link = link.."|"..(place.terse or name)
		elseif place.label then
			link = link.."|"..place.label
		end
		return link.."]]"
	end
	return nil
end

function m._get_places(frame, args, places_args)
	if (places_args.all and string.lower(places_args.all) == "true") then
		return m_places_json
	elseif places_args.name ~= nil then
		local place = m._get_place(frame, args, places_args.name)
		if place then
			if (place.name and string.lower(places_args.name) == string.lower(m_ds._get_entity_name(frame, args, place, places_args.name))) then
				return { [places_args.name] = place }
			end
		end
	elseif places_args.page ~= nil then
		local place = m._get_place(frame, args, places_args.page)
		if place then
			if (place.page and places_args.page == m_ds._get_entity_page(frame, args, place, places_args.page)) then
				return { [places_args.page] = place }
			end
		end
	end
	return nil
end

m.places_map = {}

for key, place in pairs(m_places_json) do
	m.places_map[string.lower(key)] = place
	if place.demonym then
		if m.places_map[string.lower(place.demonym)] then
			mw.log("Warning: Duplicate keys found: "..place.demonym)
		else
			m.places_map[string.lower(place.demonym)] = place
		end
	end
end

return m