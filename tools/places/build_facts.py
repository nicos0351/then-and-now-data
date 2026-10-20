"""Add facts about airports, dams and mountain passes to data.json (the
Then & Now Plus "Facts" section).

Run:  python tools/places/build_facts.py data.json <osm folder> <wikidata folder>

<osm folder> has osm_airports.json, osm_passes.json and osm_pass_roads.json
(research-places branch); <wikidata folder> has wikidata_airports.json,
wikidata_dams.json and wikidata_passes.json (research-facts branch). Dams
also use tools/places/wikipedia_dam_facts.txt.

Writes a top-level "facts" list: one entry per place that has at least one
fact, {"key", "facts": [[label, value], ...], "sources": [urls]}. Apps that
don't know about facts ignore it.

Sources: Wikidata (CC0), OpenStreetMap contributors (ODbL), Wikipedia.
"""
import json
import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
data_path, osm_dir, wd_dir = sys.argv[1:4]
data = json.load(open(data_path, encoding="utf-8"))
places = [t for t in data["towns"] if t.get("kind", "town") != "town"]


def load(folder, name, kind):
    return json.load(open(os.path.join(folder, name), encoding="utf-8"))[kind]


def km(a, b, c, d):
    return math.hypot((a - c) * 111, (b - d) * 111 * math.cos(math.radians(a)))


def coord(row):
    m = re.match(r"Point\(([-\d.]+) ([-\d.]+)\)", row.get("coord", ""))
    return (float(m.group(2)), float(m.group(1))) if m else (None, None)


def metres(v, unit="metre"):
    """Wikidata gives some heights in feet; the app always shows metres."""
    value = float(v)
    if unit == "foot":
        value *= 0.3048
    elif unit not in ("metre", None, ""):
        raise ValueError(f"unexpected unit {unit}")
    return f"{value:,.0f} m"


def wd_height(row, field):
    """(value, unit) from a Wikidata row, or (None, None)."""
    if row and row.get(field):
        return row[field], row.get(field + "Unit", "metre")
    return None, None


def year(v):
    m = re.match(r"(\d{4})", v or "")
    return m.group(1) if m else None


def key(name, kind):
    n = re.sub(r"\(.*?\)", " ", name.lower()).replace("ë", "e").replace("é", "e").replace("neck", "nek")
    if kind == "dam":
        n = re.sub(r"\b(dam|dams|reservoir|weir|barrage|lower|upper)\b", " ", n)
        return re.sub(r"[^a-z]", "", n)
    n = re.sub(r"(pass|pas)$", "", re.sub(r"[^a-z]", "", n))
    n = re.sub(r"s(?=(berg|kloof|nek|hoogte|poort)$)", "", n)
    return re.sub(r"s$", "", n.replace("rivier", "river").replace("grass", "gras"))


def osm_id(place):
    m = re.search(r"openstreetmap\.org/((?:node|way|relation)/\d+)", place.get("source", ""))
    return m.group(1) if m else None


PROVINCE = {"KZN": "KwaZulu-Natal", "MP": "Mpumalanga"}
osm_airport_rows = load(osm_dir, "osm_airports.json", "airports")
osm_airports = {e["osm"]: e["tags"] for e in osm_airport_rows}


def centre(el):
    if el.get("lat") is not None:
        return el["lat"], el["lon"]
    b = el["bounds"]
    return (b["minlat"] + b["maxlat"]) / 2, (b["minlon"] + b["maxlon"]) / 2


def airport_tags(place):
    """OSM tags for an airport: by its OSM link, else the coded airport
    within 5 km (for pins that came from earlier research)."""
    oid = osm_id(place)
    if oid:
        return osm_airports.get(oid, {})
    near = [(km(place["latitude"], place["longitude"], *centre(e)), e) for e in osm_airport_rows
            if e["tags"].get("icao") and (e.get("lat") is not None or e.get("bounds"))]
    near = [n for n in near if n[0] <= 5]
    return min(near, key=lambda n: n[0])[1]["tags"] if near else {}
osm_passes = {e["osm"]: e["tags"] for e in load(osm_dir, "osm_passes.json", "passes")}
osm_roads = {e["osm"]: e["tags"] for e in load(osm_dir, "osm_pass_roads.json", "pass_roads")}
# Roads and paths within 400 m of each pass (research-pass-roads branch).
_roads_path = os.path.join(osm_dir, "osm_roads_at_passes.json")
roads_at_passes = json.load(open(_roads_path, encoding="utf-8")) if os.path.exists(_roads_path) else {}

PAVED = {"asphalt", "paved", "concrete", "chipseal", "concrete:plates", "concrete:lanes", "paving_stones", "sett",
         "metal"}
UNPAVED = {"gravel", "unpaved", "compacted", "fine_gravel", "pebblestone", "rock", "dirt", "ground", "earth",
           "sand", "mud", "grass"}
ROAD_RANK = ["motorway", "trunk", "primary", "secondary", "tertiary", "unclassified", "residential", "service",
             "track", "bridleway", "path", "footway"]
# Main roads in South Africa are tarred unless mapped otherwise.
TARRED_BY_DEFAULT = {"motorway", "trunk", "primary"}


def road_kind(tags):
    """'tar', 'gravel', 'track', 'foot' or None (unknown) for one way."""
    surface = tags.get("surface", "")
    highway = tags.get("highway", "")
    if surface in PAVED:
        return "tar"
    if highway in ("path", "footway", "bridleway"):
        return "foot"
    if surface in UNPAVED:
        return "track" if highway == "track" else "gravel"
    if highway == "track":
        return "track"
    if highway in TARRED_BY_DEFAULT:
        return "tar"
    return None


def pass_route(place):
    """(road number, surface label) for the road or path over a pass."""
    ways = [w for w in roads_at_passes.get(place["key"], []) if w["tags"].get("highway") in ROAD_RANK]
    if not ways:
        return None, None
    k = key(place["name"], "pass")
    named = [w for w in ways if w["tags"].get("name") and key(w["tags"]["name"], "pass") == k]
    if named:
        route = named
    else:
        best = min(ROAD_RANK.index(w["tags"]["highway"]) for w in ways)
        route = [w for w in ways if ROAD_RANK.index(w["tags"]["highway"]) == best]
    kinds = {road_kind(w["tags"]) for w in route} - {None}
    refs = [w["tags"]["ref"] for w in route if w["tags"].get("ref")]
    ref = max(set(refs), key=refs.count).replace(";", " / ") if refs else None
    if not kinds:
        label = None
    elif kinds == {"foot"}:
        label = "Footpath only (hiking)"
    elif kinds == {"tar"}:
        label = "Tarred"
    elif "tar" in kinds:
        label = "Partly tarred, partly gravel"
    elif kinds <= {"track", "foot"}:
        label = "Dirt track"
    else:
        label = "Gravel"
    return ref, label
wd_airports = {r["icao"]: r for r in load(wd_dir, "wikidata_airports.json", "airports") if r.get("icao")}
wd_dams = load(wd_dir, "wikidata_dams.json", "dams")
wd_passes = load(wd_dir, "wikidata_passes.json", "passes")

wiki_dams = {}
for line in open(os.path.join(HERE, "wikipedia_dam_facts.txt"), encoding="utf-8"):
    line = line.strip()
    if not line or line.startswith("#"):
        continue
    name, river, prov, yr, ml, height = line.split(";")
    wiki_dams.setdefault(key(name, "dam"), []).append(
        {"river": river, "province": PROVINCE.get(prov, prov), "year": yr, "ml": ml, "height": height})
DAM_LIST = "https://en.wikipedia.org/wiki/List_of_dams_in_South_Africa"


def nearest_wd(rows, place, kind, radius_same_name, radius_any):
    lat, lon = place["latitude"], place["longitude"]
    k = key(place["name"], kind)
    best, best_d = None, None
    for r in rows:
        rlat, rlon = coord(r)
        if rlat is None:
            continue
        d = km(lat, lon, rlat, rlon)
        same = key(r.get("name", ""), kind) == k
        if (same and d <= radius_same_name) or d <= radius_any:
            if best is None or d < best_d:
                best, best_d = r, d
    return best


def capacity(ml):
    ml = float(ml)
    if ml >= 1000:
        mcm = ml / 1000
        return f"{mcm:,.1f} million m³" if mcm < 10 else f"{mcm:,.0f} million m³"
    return f"{ml:,.0f} million litres"


DAM_TYPES = {"arch dam": "Arch", "gravity dam": "Concrete gravity", "embankment dam": "Earth embankment"}

entries = []
for p in places:
    facts, sources = [], []
    wd = None
    if p["kind"] == "airport":
        tags = airport_tags(p)
        icao = tags.get("icao")
        wd = wd_airports.get(icao) if icao else None
        iata = tags.get("iata") or (wd or {}).get("iata")
        icao = icao or (wd or {}).get("icao")
        if iata or icao:
            facts.append(["Airport codes", " · ".join(c for c in (iata, icao) if c)])
        ele, unit = wd_height(wd, "elevation")
        if ele is None and tags.get("ele"):
            ele, unit = re.sub(r"[^\d.]", "", tags["ele"]), "metre"
        if ele:
            try:
                facts.append(["Height above sea level", metres(ele, unit)])
            except ValueError:
                pass
        operator = (wd or {}).get("operator") or tags.get("operator")
        if operator:
            facts.append(["Run by", operator])
        opened = year((wd or {}).get("opened") or (wd or {}).get("inception"))
        if opened:
            facts.append(["Opened", opened])
    elif p["kind"] == "dam":
        k = key(p["name"], "dam")
        rows = wiki_dams.get(k, [])
        if len(rows) > 1:
            rows = [r for r in rows if r["province"] in ("", p["province"])] or []
        w = rows[0] if len(rows) == 1 else None
        wd = nearest_wd(wd_dams, p, "dam", 5, 0.5)
        if w and w["river"]:
            facts.append(["River", w["river"]])
        elif wd and wd.get("river"):
            facts.append(["River", wd["river"]])
        completed = (w or {}).get("year") or year((wd or {}).get("service") or (wd or {}).get("opened")
                                                  or (wd or {}).get("inception"))
        if completed:
            facts.append(["Completed", completed])
        if w and w["ml"]:
            facts.append(["Capacity", capacity(w["ml"])])
        height, unit = ((w["height"], "metre") if w and w["height"] else wd_height(wd, "height"))
        if height:
            facts.append(["Wall height", metres(height, unit)])
        kind = DAM_TYPES.get((wd or {}).get("type", ""))
        if kind:
            facts.append(["Wall type", kind])
        if w:
            sources.append(DAM_LIST)
    elif p["kind"] == "pass":
        tags = {}
        oid = osm_id(p)
        if oid:
            tags = osm_passes.get(oid) or osm_roads.get(oid) or {}
        wd = nearest_wd(wd_passes, p, "pass", 15, 0)
        ele, unit = wd_height(wd, "elevation")
        if ele is None and tags.get("ele"):
            ele, unit = re.sub(r"[^\d.]", "", tags["ele"]), "metre"
        if ele:
            try:
                facts.append(["Height at the top", metres(ele, unit)])
            except ValueError:
                pass
        if wd and wd.get("range"):
            facts.append(["Mountain range", wd["range"]])
        ref, surface = pass_route(p)
        ref = ref or (tags.get("ref") or "").replace(";", " / ") or None
        if ref:
            facts.append(["Road", ref])
        if surface is None and tags.get("surface"):
            surface = {"tar": "Tarred", "gravel": "Gravel", "track": "Dirt track", "foot": "Footpath only (hiking)"}.get(
                road_kind(tags))
        if surface:
            facts.append(["Road surface", surface])
    if not facts:
        continue
    if wd and wd.get("enwiki"):
        sources.insert(0, wd["enwiki"])
    if wd:
        sources.append(wd["item"].replace("http://", "https://"))
    if osm_id(p):
        sources.append(p["source"])
    entries.append({"key": p["key"], "facts": facts, "sources": list(dict.fromkeys(sources))})

data["facts"] = entries
json.dump(data, open(data_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
counts = {k: sum(1 for e in entries for p in places if p["key"] == e["key"] and p["kind"] == k)
          for k in ("airport", "dam", "pass")}
print(counts, "of", {k: sum(1 for p in places if p["kind"] == k) for k in ("airport", "dam", "pass")})
