"""Research helper: download South Africa's airports, dams and mountain
passes from OpenStreetMap, so the map can show all of them (renamed or not).

Run by the manual "Research: airports, dams and passes (OpenStreetMap)"
workflow. It makes three queries to the public Overpass API (be gentle:
don't schedule this) and writes out/osm_<kind>.json with each element's
tags, centre and bounding box.

Data (c) OpenStreetMap contributors, ODbL.
"""
import json
import os
import sys
import time
import urllib.parse
import urllib.request

ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]
AREA = 'area["ISO3166-1"="ZA"][admin_level=2]->.za;'
QUERIES = {
    "airports": "nwr(area.za)[aeroway=aerodrome][name];",
    "dams": ("(nwr(area.za)[water=reservoir][name]; nwr(area.za)[landuse=reservoir][name];"
             " nwr(area.za)[waterway=dam][name];);"),
    "passes": ("(node(area.za)[mountain_pass=yes][name]; node(area.za)[natural=saddle][name];"
               " way(area.za)[mountain_pass=yes][name];);"),
    # Many passes are only named on the road itself ("Magoebaskloof Pass").
    "pass_roads": ('way(area.za)[highway~"^(motorway|trunk|primary|secondary|tertiary|unclassified|track)$"]'
                   '[name~"([Pp]ass|pas|[Pp]oort|[Nn]ek|hoogte)$"];'),
}
USER_AGENT = "then-and-now-data research (github.com/nicos0351/then-and-now-data)"


def fetch(body):
    query = f"[out:json][timeout:600];{AREA}{body}out tags center bb;"
    data = urllib.parse.urlencode({"data": query}).encode()
    last = None
    for url in ENDPOINTS:
        for attempt in range(3):
            try:
                req = urllib.request.Request(url, data=data, headers={"User-Agent": USER_AGENT})
                with urllib.request.urlopen(req, timeout=700) as r:
                    return json.loads(r.read().decode("utf-8"))
            except Exception as e:  # noqa: BLE001 - research script, retry anything
                last = e
                print(f"{url} attempt {attempt + 1} failed: {e}", file=sys.stderr)
                time.sleep(30 * (attempt + 1))
    raise SystemExit(f"All Overpass endpoints failed: {last}")


def main():
    os.makedirs("out", exist_ok=True)
    for kind, body in QUERIES.items():
        result = fetch(body)
        rows = []
        for el in result.get("elements", []):
            centre = el.get("center") or {"lat": el.get("lat"), "lon": el.get("lon")}
            rows.append({
                "osm": f"{el['type']}/{el['id']}",
                "lat": centre.get("lat"),
                "lon": centre.get("lon"),
                "bounds": el.get("bounds"),
                "tags": el.get("tags", {}),
            })
        json.dump({"source": "OpenStreetMap contributors (ODbL)", kind: rows},
                  open(f"out/osm_{kind}.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(kind, len(rows))
        time.sleep(20)


if __name__ == "__main__":
    main()
