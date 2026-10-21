"""Research helper: how many "things to see" do the open sources have for a
sample of South African towns? Decides whether a "Things to see" section
in the town sheet is worth building.

Run by the manual "Research: things to see (sample)" workflow. For each
sample town it asks:
  - OpenStreetMap (Overpass): named museums, monuments, memorials, historic
    buildings, viewpoints, nature reserves, waterfalls and so on within a
    radius that suits the town's size (ODbL);
  - Wikidata: items with a position in that radius that have an English
    Wikipedia article, and which are declared heritage (CC0);
  - Wikivoyage: whether the town has a travel guide page and how many
    "See" / "Do" listings it has (CC BY-SA).
Writes out/sights_sample.json and out/summary.md.
"""
import json
import re
import sys
import time
import urllib.parse
import urllib.request

USER_AGENT = "then-and-now-data research (github.com/nicos0351/then-and-now-data)"
OVERPASS = ["https://overpass-api.de/api/interpreter", "https://overpass.kumi.systems/api/interpreter"]
WIKIDATA = "https://query.wikidata.org/sparql"
WIKIVOYAGE = "https://en.wikivoyage.org/w/api.php"

# name (as in the app), Wikivoyage titles to try, lat, lon, population, what it stands for
TOWNS = [
    ("Robert Sobukwe Town", ["Graaff-Reinet"], -32.25215, 24.53075, 62896, "Karoo tourist town (renamed 2026)"),
    ("Makhanda", ["Makhanda", "Grahamstown"], -33.30422, 26.53276, 91548, "university / heritage town (renamed)"),
    ("Knysna", ["Knysna"], -34.03627, 23.04713, 68659, "Garden Route tourist town"),
    ("Clarens", ["Clarens"], -28.5154, 28.41985, 7644, "small tourist village"),
    ("Prince Albert", ["Prince Albert"], -33.22476, 22.02673, 13136, "small Karoo town"),
    ("Nxuba", ["Cradock", "Nxuba"], -32.16422, 25.61918, 43936, "Karoo town (renamed)"),
    ("Lady Grey", ["Lady Grey"], -30.71084, 27.21613, 8414, "small rural Eastern Cape town"),
    ("Calvinia", ["Calvinia"], -31.47069, 19.77601, 8146, "remote Northern Cape town"),
    ("Mbombela", ["Mbombela", "Nelspruit"], -25.47512, 30.96935, 110159, "provincial capital (renamed)"),
    ("Polokwane", ["Polokwane", "Pietersburg"], -23.90449, 29.46885, 272461, "provincial capital (renamed)"),
    ("Pretoria", ["Pretoria"], -25.74486, 28.18783, 2112693, "big city"),
    ("Komani", ["Komani", "Queenstown (South Africa)"], -31.89756, 26.87533, 118599, "regional town (renamed)"),
    ("Mthatha", ["Mthatha", "Umtata"], -31.58893, 28.78443, 164848, "rural Eastern Cape city (renamed)"),
    ("Bela-Bela", ["Bela-Bela", "Warmbaths"], -24.88333, 28.28333, 90210, "holiday town (renamed)"),
    ("eMkhondo", ["eMkhondo", "Piet Retief"], -27.00706, 30.81323, 84349, "farming town (renamed)"),
]


def radius_m(pop):
    if pop < 20000:
        return 3000
    if pop < 150000:
        return 5000
    if pop < 1000000:
        return 7000
    return 8000


def get(url, data=None, tries=4):
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, data=data, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=180) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:  # noqa: BLE001
            print(f"  retry {attempt + 1} for {url[:60]}: {e}", file=sys.stderr)
            time.sleep(15 * (attempt + 1))
    return None


# --- OpenStreetMap -------------------------------------------------------

def osm_query(lat, lon, r):
    a = f"(around:{r},{lat},{lon})"
    sel = [
        'tourism~"^(attraction|museum|viewpoint|artwork|gallery|zoo|theme_park|picnic_site|information)$"',
        "historic",
        'leisure~"^(nature_reserve|park|garden)$"',
        'boundary="protected_area"',
        'natural~"^(waterfall|cave_entrance|peak|hot_spring|beach)$"',
        "heritage",
    ]
    parts = "".join(f'nwr[{s}][name]{a};' for s in sel)
    return f"[out:json][timeout:120];({parts});out center tags;"


def classify(tags):
    t, h = tags.get("tourism"), tags.get("historic")
    if t == "museum":
        return "museum"
    if t == "gallery":
        return "gallery"
    if t == "information":
        return "tourist info" if tags.get("information") == "office" else None  # skip boards and signposts
    if h in ("memorial", "monument"):
        return "monument / memorial"
    if h in ("battlefield", "fort", "castle", "archaeological_site", "ruins"):
        return "historic site"
    if h or tags.get("heritage"):
        return "historic building / site"
    if t == "viewpoint" or tags.get("natural") == "peak":
        return "viewpoint / peak"
    if tags.get("natural") in ("waterfall", "cave_entrance", "hot_spring", "beach"):
        return "nature feature"
    if tags.get("leisure") == "nature_reserve" or tags.get("boundary") == "protected_area":
        return "nature reserve"
    if tags.get("leisure") in ("park", "garden"):
        return "park / garden"
    if t == "artwork":
        return "artwork"
    if t in ("attraction", "zoo", "theme_park"):
        return "attraction"
    if t == "picnic_site":
        return "picnic site"
    return None


def fetch_osm(lat, lon, r):
    q = osm_query(lat, lon, r)
    for url in OVERPASS:
        res = get(url, urllib.parse.urlencode({"data": q}).encode())
        if res is not None:
            break
        time.sleep(30)
    if res is None:
        return None
    seen, out = set(), []
    for e in res.get("elements", []):
        tags = e.get("tags", {})
        cat = classify(tags)
        name = tags.get("name", "").strip()
        if not cat or not name or (name.lower(), cat) in seen:
            continue
        seen.add((name.lower(), cat))
        c = e.get("center") or {"lat": e.get("lat"), "lon": e.get("lon")}
        out.append({
            "name": name, "category": cat, "lat": c.get("lat"), "lon": c.get("lon"),
            "osm": f"{e['type']}/{e['id']}", "wikidata": tags.get("wikidata"),
            "wikipedia": tags.get("wikipedia"), "description": tags.get("description"),
        })
    return out


# --- Wikidata ------------------------------------------------------------

SKIP_CLASSES = ("human settlement", "town", "city", "suburb", "village", "neighborhood", "school",
                "high school", "primary school", "road", "street", "railway station", "hospital",
                "local municipality", "electoral ward", "ward", "main place", "sub place",
                "business", "company", "radio station", "airport", "dam", "mountain pass")


def fetch_wikidata(lat, lon, r):
    km = r / 1000
    q = f"""
SELECT ?item ?itemLabel (SAMPLE(?cls) AS ?class) (SAMPLE(?article) AS ?article) (SAMPLE(?her) AS ?heritage) WHERE {{
  SERVICE wikibase:around {{ ?item wdt:P625 ?loc . bd:serviceParam wikibase:center "Point({lon} {lat})"^^geo:wktLiteral . bd:serviceParam wikibase:radius "{km}" . }}
  OPTIONAL {{ ?item wdt:P31 ?c . ?c rdfs:label ?cls . FILTER(LANG(?cls) = "en") }}
  OPTIONAL {{ ?article schema:about ?item ; schema:isPartOf <https://en.wikipedia.org/> . }}
  OPTIONAL {{ ?item wdt:P1435 ?h . ?h rdfs:label ?her . FILTER(LANG(?her) = "en") }}
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en" . }}
}} GROUP BY ?item ?itemLabel
"""
    res = get(WIKIDATA + "?" + urllib.parse.urlencode({"query": q, "format": "json"}))
    if res is None:
        return None
    out = []
    for b in res["results"]["bindings"]:
        cls = b.get("class", {}).get("value", "")
        if any(s == cls.lower() or cls.lower().endswith(" " + s) for s in SKIP_CLASSES):
            continue
        out.append({
            "name": b["itemLabel"]["value"], "class": cls,
            "item": b["item"]["value"].rsplit("/", 1)[-1],
            "article": b.get("article", {}).get("value"),
            "heritage": b.get("heritage", {}).get("value"),
        })
    return out


# --- Wikivoyage ----------------------------------------------------------

def fetch_wikivoyage(titles):
    for title in titles:
        res = get(WIKIVOYAGE + "?" + urllib.parse.urlencode({
            "action": "query", "prop": "revisions", "rvprop": "content", "rvslots": "main",
            "titles": title, "redirects": 1, "format": "json", "formatversion": 2}))
        if not res:
            continue
        pages = res.get("query", {}).get("pages", [])
        if not pages or pages[0].get("missing"):
            continue
        page = pages[0]
        text = page["revisions"][0]["slots"]["main"]["content"]
        counts = {k: len(re.findall(r"\{\{\s*" + k + r"\s*\|", text, re.I)) for k in ("see", "do", "listing")}
        status = re.search(r"\{\{\s*(outline|usable|guide|star)city|\{\{\s*(outline|usable|guide|star)", text, re.I)
        return {"title": page["title"], "see": counts["see"], "do": counts["do"],
                "status": (status.group(1) or status.group(2)).lower() if status else None,
                "url": "https://en.wikivoyage.org/wiki/" + urllib.parse.quote(page["title"].replace(" ", "_"))}
    return None


def main():
    results = []
    for name, wv_titles, lat, lon, pop, what in TOWNS:
        r = radius_m(pop)
        print(f"{name} ({r} m)...", file=sys.stderr)
        osm = fetch_osm(lat, lon, r)
        time.sleep(5)
        wd = fetch_wikidata(lat, lon, r)
        time.sleep(2)
        wv = fetch_wikivoyage(wv_titles)
        results.append({"town": name, "what": what, "population": pop, "radius_m": r,
                        "osm": osm, "wikidata": wd, "wikivoyage": wv})
        time.sleep(5)

    import os
    os.makedirs("out", exist_ok=True)
    with open("out/sights_sample.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=1)

    lines = ["# Things to see: sample of 15 towns", "",
             "| Town | Kind | OSM sights | of which museums / historic / monuments | nature | Wikidata with Wikipedia article | heritage | Wikivoyage see + do |",
             "|---|---|---|---|---|---|---|---|"]
    for t in results:
        osm = t["osm"] or []
        hist = sum(1 for o in osm if o["category"] in ("museum", "gallery", "monument / memorial", "historic site", "historic building / site"))
        nat = sum(1 for o in osm if o["category"] in ("nature reserve", "nature feature", "viewpoint / peak"))
        wd = t["wikidata"] or []
        art = sum(1 for w in wd if w["article"])
        her = sum(1 for w in wd if w["heritage"])
        wv = t["wikivoyage"]
        wvs = f'{wv["see"]} + {wv["do"]} ({wv["status"] or "?"})' if wv else "no page"
        lines.append(f'| {t["town"]} | {t["what"]} | {len(osm) if t["osm"] is not None else "failed"} | {hist} | {nat} | '
                     f'{art if t["wikidata"] is not None else "failed"} | {her} | {wvs} |')
    with open("out/summary.md", "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
