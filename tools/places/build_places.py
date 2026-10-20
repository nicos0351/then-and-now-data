"""Add South Africa's airports, dams and mountain passes to data.json.

Run:  python tools/places/build_places.py data.json <research folder>

<research folder> holds osm_airports.json, osm_dams.json, osm_passes.json and
osm_pass_roads.json
from the "Research: airports, dams and passes (OpenStreetMap)" workflow
(the research-places branch). Places already in data.json (the renamed
airports, dams and pass) are kept as they are; everything else is added as
a plain pin, except the renames listed in RENAMES.

What counts:
- airports: every aerodrome with an official ICAO or IATA code, except
  closed ones (this leaves out private farm strips);
- dams: every named reservoir on Wikipedia's list of South African dams,
  plus any other named "... Dam" at least 2 km across;
- passes: every named mountain pass, named saddles called a pass, nek,
  hoogte, poort, kloof or gap, and roads named as a pass, poort, nek or
  hoogte (one pin per pass, English and Afrikaans spellings merged).

Data (c) OpenStreetMap contributors, ODbL.
"""
import json
import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
data_path, research = sys.argv[1], sys.argv[2]
data = json.load(open(data_path, encoding="utf-8"))
towns = data["towns"]
outline = json.load(open(os.path.join(HERE, "provinces.json"), encoding="utf-8"))

OSM = "https://www.openstreetmap.org/"


def load(kind):
    return json.load(open(os.path.join(research, f"osm_{kind}.json"), encoding="utf-8"))[kind]


def centre(el):
    if el.get("lat") is not None:
        return el["lat"], el["lon"]
    b = el["bounds"]
    return (b["minlat"] + b["maxlat"]) / 2, (b["minlon"] + b["maxlon"]) / 2


def across_km(el):
    b = el.get("bounds")
    if not b:
        return 0.0
    lat = (b["minlat"] + b["maxlat"]) / 2
    dy = (b["maxlat"] - b["minlat"]) * 111
    dx = (b["maxlon"] - b["minlon"]) * 111 * math.cos(math.radians(lat))
    return math.hypot(dx, dy)


def km(a, b, c, d):
    return math.hypot((a - c) * 111, (b - d) * 111 * math.cos(math.radians(a)))


# --- Province lookup (point in polygon, nearest town as a fallback) -----

def inside(lon, lat, ring):
    hit = False
    j = len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i]
        xj, yj = ring[j]
        if (yi > lat) != (yj > lat) and lon < (xj - xi) * (lat - yi) / (yj - yi) + xi:
            hit = not hit
        j = i
    return hit


def province(lat, lon):
    for p in outline["provinces"]:
        for part in p["polygons"]:
            if inside(lon, lat, part["outer"]) and not any(inside(lon, lat, h) for h in part["holes"]):
                return p["name"]
    near = min((t for t in towns if t.get("kind", "town") == "town"),
               key=lambda t: km(lat, lon, t["latitude"], t["longitude"]))
    return near["province"]


# --- Names ----------------------------------------------------------------

STOP = r"\b(dam|dams|dame|reservoir|weir|barrage|cofferdam|storage|lower|upper|the)\b"


def dam_key(name):
    n = re.sub(r"\(.*?\)", " ", name.lower())
    n = re.sub(STOP, " ", n)
    n = re.sub(r"[^a-z]", "", n.replace("ë", "e").replace("é", "e"))
    return n


def tidy(name):
    name = re.sub(r"\s*\((closed|disused)\)\s*$", "", name, flags=re.I).strip()
    name = re.sub(r"\bdam\b$", "Dam", name)
    return re.sub(r"\s+", " ", name)


wiki = set()
for line in open(os.path.join(HERE, "wikipedia_dams.txt"), encoding="utf-8"):
    line = line.strip()
    if line and not line.startswith("#"):
        wiki.add(dam_key(line))

# Renamed places found in OpenStreetMap's old_name tags and confirmed in a
# second source. Matched by ICAO code (airports) or dam name key.
RENAMES = {
    "FABL": ("Bloemfontein International Airport", 2012,
             "https://www.news24.com/bloem-airport-officially-renamed-20121213"),
    "FAGG": ("P. W. Botha Airport", None, "https://en.wikipedia.org/wiki/George_Airport"),
    "FAUT": ("K. D. Matanzima Airport", None,
             "https://www.dispatchlive.co.za/news/2017-09-30-rename-mthatha-airport-after-matanzima-says-mandla-mandela/"),
    "FAUP": ("Pierre van Ryneveld Airport", None, "https://en.wikipedia.org/wiki/Upington_Airport"),
    "kouga": ("Paul Sauer Dam", 1995, "https://en.wikipedia.org/wiki/Kouga_Dam"),
    "ntshingwayo": ("Chelmsford Dam", 2000,
                    "https://www.dws.gov.za/Communications/MinisterSpeeches/Kasrils/2000/Ntshingwayo-Dam-Speech.pdf"),
    "mokolo": ("Hans Strijdom Dam", None, "https://en.wikipedia.org/wiki/Mokolo_Dam"),
    "tzaneen": ("Fanie Botha Dam", None, "https://en.wikipedia.org/wiki/Tzaneen_Dam"),
    "nqweba": ("Van Ryneveld's Pass Dam", None, "https://en.wikipedia.org/wiki/List_of_dams_in_South_Africa"),
    "solplaatje": ("Saulspoort Dam", None, "https://en.wikipedia.org/wiki/List_of_dams_in_South_Africa"),
    "tyumbu": ("Kraai River Pass", 2026,
               "https://businesstech.co.za/news/government/850166/east-london-and-graaff-reinet-are-officially-no-more/"),
}
NOTES = {
    "tyumbu": "Gazetted 6 Feb 2026 with the other Eastern Cape renames, which are under review after more than "
              "38,000 objections (as of May 2026).",
}
STORIES = {
    "ntshingwayo": ("Honours Inkosi Ntshingwayo kaMahole Khoza, a senior general in King Cetshwayo's army "
                    "who commanded at the Battle of Isandlwana in 1879.",
                    ["https://www.dws.gov.za/Communications/MinisterSpeeches/Kasrils/2000/Ntshingwayo-Dam-Speech.pdf"]),
    "kouga": (None, ["https://en.wikipedia.org/wiki/Kouga_Dam"]),
}

# --- Pick the places -----------------------------------------------------

existing = [t for t in towns if t.get("kind", "town") != "town"]


def already_there(kind, lat, lon, radius):
    return any(t.get("kind") == kind and km(lat, lon, t["latitude"], t["longitude"]) < radius for t in existing)


picked = []  # (kind, name, lat, lon, osm id, match key)

# Airports
airports = {}
for el in load("airports"):
    t = el["tags"]
    code = t.get("icao") or t.get("iata")
    if not code or re.search(r"closed|disused", t["name"], re.I) or t.get("disused") or t.get("abandoned"):
        continue
    lat, lon = centre(el)
    key = t.get("icao") or t["iata"]
    if key in airports:
        continue
    airports[key] = ("airport", tidy(t["name"]), lat, lon, el["osm"], key)
for a in airports.values():
    if not already_there("airport", a[2], a[3], 5):
        picked.append(a)

# Dams: the reservoir (or dam wall when no reservoir is mapped), one per name.
dams = {}
for el in load("dams"):
    t = el["tags"]
    name = t["name"]
    key = dam_key(name)
    if not key:
        continue
    is_wall = bool(t.get("waterway"))
    size = 0.0 if is_wall else across_km(el)
    listed = key in wiki
    if not listed and not (size >= 2 and re.search(r"\bdam\b", name, re.I)):
        continue
    lat, lon = centre(el)
    best = dams.get(key)
    # Same name far apart = different dams (e.g. two Rietvlei Dams).
    if best and km(lat, lon, best["lat"], best["lon"]) > 40:
        key = f"{key}@{round(lat, 1)},{round(lon, 1)}"
        best = dams.get(key)
    score = (0 if is_wall else 1, size)
    if best is None or score > best["score"]:
        dams[key] = {"name": tidy(name), "lat": lat, "lon": lon, "osm": el["osm"], "score": score,
                     "match": key.split("@")[0]}
def dam_already_there(d):
    # Big dams are long: the same dam can be mapped far from an existing pin.
    return already_there("dam", d["lat"], d["lon"], 20) or any(
        t.get("kind") == "dam" and dam_key(t["name"]) == d["match"]
        and km(d["lat"], d["lon"], t["latitude"], t["longitude"]) < 80 for t in existing)


for d in dams.values():
    if not dam_already_there(d):
        picked.append(("dam", d["name"], d["lat"], d["lon"], d["osm"], d["match"]))

# Passes: named pass points first, then roads named as passes where no
# point is mapped. English and Afrikaans spellings count as one pass
# ("Du Toitskloof Pass" = "Dutoitskloofpas").
PASSY = re.compile(r"pass|pas\b|nek|neck|hoogte|poort|kloof|gap", re.I)


def pass_key(name):
    n = name.lower().replace("ë", "e")
    n = re.sub(r"(pass|pas)$", "", re.sub(r"[^a-z]", "", n.replace("neck", "nek")))
    # "Naudesberg"/"Naudeberg", "Naude's Nek"/"Naudesnek".
    n = re.sub(r"s(?=(berg|kloof|nek|hoogte|poort)$)", "", n)
    # "Hex River Pass"/"Hexrivierpas", "Grassneck"/"Grasnek", "Joubert's"/"Joubert".
    n = n.replace("rivier", "river").replace("grass", "gras")
    return re.sub(r"s$", "", n)


passes = []


def add_pass(name, lat, lon, osm, near_km=0.0):
    key = pass_key(name)
    if any(pass_key(p[1]) == key and km(lat, lon, p[2], p[3]) < 25 for p in passes):
        return
    # A different spelling of a pass that's already in (Wikipedia list only).
    if near_km and any(km(lat, lon, p[2], p[3]) < near_km for p in passes):
        return
    passes.append(("pass", name, lat, lon, osm, key))


for el in load("passes"):
    t = el["tags"]
    if t.get("mountain_pass") != "yes" and not PASSY.search(t["name"]):
        continue
    lat, lon = centre(el)
    add_pass(tidy(t["name"]), lat, lon, el["osm"])

# Roads: join the pieces of each named pass road, and use the piece nearest
# the middle of the road.
groups = []
for el in load("pass_roads"):
    name = tidy(el["tags"]["name"])
    if re.search(r"bypass$", name, re.I):  # town bypass roads, not passes
        continue
    lat, lon = centre(el)
    for g in groups:
        if pass_key(g["name"]) == pass_key(name) and any(km(lat, lon, a, b) < 15 for a, b, _ in g["parts"]):
            g["parts"].append((lat, lon, el["osm"]))
            break
    else:
        groups.append({"name": name, "parts": [(lat, lon, el["osm"])]})
for g in groups:
    mid_lat = sum(p[0] for p in g["parts"]) / len(g["parts"])
    mid_lon = sum(p[1] for p in g["parts"]) / len(g["parts"])
    lat, lon, osm = min(g["parts"], key=lambda p: km(p[0], p[1], mid_lat, mid_lon))
    add_pass(g["name"], lat, lon, osm)

# Wikipedia's lists of passes (with coordinates) fill the gaps, e.g.
# Magoebaskloof, Meiringspoort and Prince Alfred Pass.
wiki_source = None
for line in open(os.path.join(HERE, "wikipedia_passes.txt"), encoding="utf-8"):
    line = line.strip()
    if line.startswith("# https://"):
        wiki_source = line[2:]
    if not line or line.startswith("#"):
        continue
    name, lat, lon = line.split(";")
    add_pass(name, float(lat), float(lon), wiki_source, near_km=1.5)

for p in passes:
    if not already_there("pass", p[2], p[3], 5):
        picked.append(p)

# --- Add them --------------------------------------------------------------

keys = {t["key"] for t in towns}
have_story = {s["key"] for s in data["stories"]}
added = {"airport": 0, "dam": 0, "pass": 0}
renamed = []
for kind, name, lat, lon, osm, match in picked:
    lat, lon = round(lat, 5), round(lon, 5)
    key = f"asset:{name.lower()}:{lat:.3f}:{lon:.3f}"
    if key in keys:
        continue
    keys.add(key)
    entry = {
        "key": key, "kind": kind, "name": name, "oldName": name, "hasKnownRename": False,
        "renamedYear": None, "reverted": False, "notes": None, "province": province(lat, lon),
        "latitude": lat, "longitude": lon, "population": 0,
        "source": osm if osm.startswith("https://") else OSM + osm,
    }
    rename = RENAMES.get(match)
    if rename:
        old, year, src = rename
        entry.update(oldName=old, hasKnownRename=True, renamedYear=year, source=src, notes=NOTES.get(match))
        renamed.append(f"{old} -> {name}")
        story = STORIES.get(match)
        if story and story[0] and key not in have_story:
            data["stories"].append({"key": key, "name": name, "say": None, "sounds": [], "meaning": story[0],
                                    "formerNameOrigin": None, "sources": story[1]})
    towns.append(entry)
    added[kind] += 1

data["dataVersion"] = 7
data["updated"] = "2026-10-19"
data["changes"].append({
    "version": 7,
    "date": "2026-10-19",
    "summary": f"All of South Africa's airports ({added['airport']} added), dams ({added['dam']}) and mountain "
               f"passes ({added['pass']}) are now on the map, with {len(renamed)} more renames such as "
               "P. W. Botha Airport → George Airport and Chelmsford Dam → Ntshingwayo Dam.",
})
json.dump(data, open(data_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(added, "renamed:", renamed)
