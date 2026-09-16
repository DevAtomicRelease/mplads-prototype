# Static assets

`india-states.geojson` — India state boundaries used by the Overview state-risk
choropleth. It is a **heavily simplified** derivative (coordinates rounded and
thinned; ~164 KB) of GADM India state polygons (via the public
`Subhash9325/GeoJson-Data-of-Indian-States` re-host). Simplified for a lightweight,
same-origin map only; not authoritative boundaries and not for any official or
legal use. State names are the base map's older labels (e.g. Orissa, Uttaranchal,
split Dadra/Daman) and are aliased to current names in the UI; Telangana and Ladakh
have no separate polygon in this base map and are left unshaded.
