"""Link our dams to the Department of Water and Sanitation's weekly
"State of Dams" stations (so the app can show a dam's level), and add the
department's dams that aren't on the map yet.

Run:  python tools/places/match_dws.py data.json <dws.json> <osm folder> <wikidata folder>

<dws.json> is made by parse_dws.py from the nine saved provincial pages
(https://www.dws.gov.za/Hydrology/Weekly/ProvinceWeek.aspx?region=..., codes
EC FS G KN LP M NC NW WC). The DWS site doesn't answer requests from
GitHub's servers, so the pages are saved by hand from South Africa when the
list of dams needs refreshing (rarely). Positions for missing dams come
from Wikidata or OpenStreetMap (research-facts / research-places branches).

Writes a top-level "damStations" list to data.json:
  [{"key": <dam key>, "region": "WC", "station": "H6R001"}, ...]
The app downloads that region's weekly page and reads the station's row.
"""
import difflib
import json
import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
data_path, dws_path, osm_dir, wd_dir = sys.argv[1:5]
data = json.load(open(data_path, encoding="utf-8"))
dws = json.load(open(dws_path, encoding="utf-8"))
outline = json.load(open(os.path.join(HERE, "provinces.json"), encoding="utf-8"))
osm = json.load(open(os.path.join(osm_dir, "osm_dams.json"), encoding="utf-8"))["dams"]
wd = json.load(open(os.path.join(wd_dir, "wikidata_dams.json"), encoding="utf-8"))["dams"]

REGION_PROVINCE = {"EC": "Eastern Cape", "FS": "Free State", "G": "Gauteng", "KN": "KwaZulu-Natal",
                   "LP": "Limpopo", "M": "Mpumalanga", "NC": "Northern Cape", "NW": "North West",
                   "WC": "Western Cape"}
NEIGHBOURS = {
    "Western Cape": {"Northern Cape", "Eastern Cape"},
    "Northern Cape": {"Western Cape", "Eastern Cape", "Free State", "North West"},
    "Eastern Cape": {"Western Cape", "Northern Cape", "Free State", "KwaZulu-Natal"},
    "Free State": {"Northern Cape", "Eastern Cape", "KwaZulu-Natal", "Mpumalanga", "Gauteng", "North West"},
    "KwaZulu-Natal": {"Eastern Cape", "Free State", "Mpumalanga"},
    "Mpumalanga": {"KwaZulu-Natal", "Free State", "Gauteng", "Limpopo"},
    "Gauteng": {"Free State", "North West", "Mpumalanga", "Limpopo"},
    "Limpopo": {"North West", "Gauteng", "Mpumalanga"},
    "North West": {"Northern Cape", "Free State", "Gauteng", "Limpopo"},
}
# The department's name -> our name, where spellings differ too much to match.
ALIASES = {
    "Vaalrivier Barrage Dam": "Vaal Barrage Dam",
    "Inyaka Dam": "Injaka Dam",
    "Setumo Dam": "Modimola Dam",  # same dam, mapped under its other name
    "Steenbras-Lower Dam": "Lower Steenbras Dam",
    "Steenbras-Upper Dam": "Steenbras Upper Dam",
    "Binfield Dam": "Binfield Park Dam",
    "Warmbad Dam": "Bela-Bela Dam",
    "Vaalharts Weir Dam": "Vaalharts Storage Weir",
}


def plain(name):
    n = re.sub(r"\(.*?\)", " ", name.lower())
    for a, b in (("ë", "e"), ("é", "e"), ("ô", "o"), ("ê", "e"), ("ï", "i")):
        n = n.replace(a, b)
    return n


def full_key(name):
    return re.sub(r"[^a-z0-9]", "", plain(name))


def short_key(name):
    n = re.sub(r"\b(dam|dams|reservoir|weir|barrage|storage|the)\b", " ", plain(name))
    n = re.sub(r"[^a-z0-9]", "", n)
    # Afrikaans/English and spelling variants: rivier/river, drift/drif, kopjes/koppies.
    return n.replace("rivier", "river").replace("drift", "drif").replace("kopjes", "koppies")


def km(a, b, c, d):
    return math.hypot((a - c) * 111, (b - d) * 111 * math.cos(math.radians(a)))


def inside(lon, lat, ring):
    hit, j = False, len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i]
        xj, yj = ring[j]
        if (yi > lat) != (yj > lat) and lon < (xj - xi) * (lat - yi) / (yj - yi) + xi:
            hit = not hit
        j = i
    return hit


def province_at(lat, lon):
    for p in outline["provinces"]:
        for part in p["polygons"]:
            if inside(lon, lat, part["outer"]) and not any(inside(lon, lat, h) for h in part["holes"]):
                return p["name"]
    return None


def nearby(province):
    return {province} | NEIGHBOURS[province]


DUPLICATES = {"https://www.openstreetmap.org/relation/2527932"}  # Brandvlei Dam reservoir (wall kept)
data["towns"] = [t for t in data["towns"] if t.get("source") not in DUPLICATES]
dams = [t for t in data["towns"] if t.get("kind") == "dam"]


def wd_position(name):
    for row in wd:
        if short_key(row.get("name", "")) == short_key(name) and coord(row):
            return coord(row)
    return None


def find_ours(name, province):
    name = ALIASES.get(name, name)
    pool = [d for d in dams if d["province"] in nearby(province)]
    for keyf in (full_key, short_key):
        hits = [d for d in pool if any(keyf(n) == keyf(name) for n in (d["name"], d["oldName"]))]
        same = [d for d in hits if d["province"] == province]
        if len(same) == 1 or (not same and len(hits) == 1):
            return (same or hits)[0], None
        if len(hits) > 1:
            # Several dams share the name: take the one where Wikidata puts it.
            pos = wd_position(name)
            if pos:
                near = [d for d in (same or hits) if km(pos[0], pos[1], d["latitude"], d["longitude"]) < 8]
                if len(near) == 1:
                    return near[0], None
            return None, f"matches {len(hits)} dams"
    # Small spelling differences ("Korentepoort"/"Korintepoort").
    scored = sorted(((difflib.SequenceMatcher(None, short_key(name), short_key(d["name"])).ratio(), d)
                     for d in pool), key=lambda s: -s[0])
    if scored and scored[0][0] >= 0.86 and (len(scored) < 2 or scored[1][0] < scored[0][0] - 0.05):
        return scored[0][1], None
    return None, None


def coord(row):
    m = re.match(r"Point\(([-\d.]+) ([-\d.]+)\)", row.get("coord", ""))
    return (float(m.group(2)), float(m.group(1))) if m else None


def centre(el):
    if el.get("lat") is not None:
        return el["lat"], el["lon"]
    b = el.get("bounds")
    return ((b["minlat"] + b["maxlat"]) / 2, (b["minlon"] + b["maxlon"]) / 2) if b else None


def find_position(name, province):
    """Where a dam that isn't on our map is: Wikidata first, then OSM."""
    k = short_key(name)
    for row in wd:
        c = coord(row)
        if c and short_key(row.get("name", "")) == k and province_at(*c) in nearby(province):
            return c, row["item"].replace("http://", "https://"), row["name"]
    best = None
    for el in osm:
        c = centre(el)
        if c and short_key(el["tags"]["name"]) == k and province_at(*c) in nearby(province):
            # Prefer the dam wall, which is where people visit.
            if best is None or el["tags"].get("waterway") == "dam":
                best = (c, "https://www.openstreetmap.org/" + el["osm"], el["tags"]["name"])
    return best if best else (None, None, None)


links, added, unmatched = {}, [], []
keys = {t["key"] for t in data["towns"]}
for region, page in dws.items():
    province = REGION_PROVINCE[region]
    for row in page["dams"]:
        name = row["name"]
        ours, problem = find_ours(name, province)
        if ours is None and problem is None:
            pos, source, mapped_name = find_position(ALIASES.get(name, name), province)
            if pos:
                # The map's spelling ("Voëlvlei Dam") reads better than the
                # department's ("Voelvlei Dam").
                if full_key(mapped_name) == full_key(name) and mapped_name != mapped_name.encode("ascii", "ignore").decode():
                    name = mapped_name
                lat, lon = round(pos[0], 5), round(pos[1], 5)
                prov = province_at(lat, lon) or province
                key = f"asset:{name.lower()}:{lat:.3f}:{lon:.3f}"
                if key not in keys:
                    ours = {"key": key, "kind": "dam", "name": name, "oldName": name, "hasKnownRename": False,
                            "renamedYear": None, "reverted": False, "notes": None, "province": prov,
                            "latitude": lat, "longitude": lon, "population": 0, "source": source}
                    data["towns"].append(ours)
                    dams.append(ours)
                    keys.add(key)
                    added.append(f"{name} ({prov})")
        if ours is None:
            unmatched.append(f"{region}: {name}" + (f" ({problem})" if problem else ""))
            continue
        old = links.get(ours["key"])
        if old and old["station"] != row["station"] and REGION_PROVINCE[old["region"]] == ours["province"]:
            continue  # listed twice: keep the row from the dam's own province
        links[ours["key"]] = {"key": ours["key"], "region": region, "station": row["station"]}

data["damStations"] = sorted(links.values(), key=lambda e: e["key"])
json.dump(data, open(data_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
total = sum(len(p["dams"]) for p in dws.values())
print(f"{total} DWS dams: linked {len(links)}; added {len(added)} new dam pins; not found {len(unmatched)}")
print("added:", "; ".join(added))
print("not found:", "; ".join(unmatched))
