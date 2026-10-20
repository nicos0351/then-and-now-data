"""Research helper: for every mountain pass in data.json, download the
roads and paths that run through it from OpenStreetMap, so each pass can
say whether it's tarred, gravel or a footpath.

Run by the manual "Research: roads at passes (OpenStreetMap)" workflow.
A few Overpass queries (passes in batches); writes out/osm_roads_at_passes.json:
{"<pass key>": [{"tags": {...}, "lat": .., "lon": ..}, ...], ...}

Data (c) OpenStreetMap contributors, ODbL.
"""
import json
import os
import sys
import time
import urllib.parse
import urllib.request

ENDPOINTS = ["https://overpass-api.de/api/interpreter", "https://overpass.kumi.systems/api/interpreter"]
USER_AGENT = "then-and-now-data research (github.com/nicos0351/then-and-now-data)"
RADIUS = 400  # metres around the pass point
HIGHWAYS = "motorway|trunk|primary|secondary|tertiary|unclassified|residential|service|track|path|footway|bridleway"


def fetch(query):
    data = urllib.parse.urlencode({"data": query}).encode()
    last = None
    for url in ENDPOINTS:
        for attempt in range(3):
            try:
                req = urllib.request.Request(url, data=data, headers={"User-Agent": USER_AGENT})
                with urllib.request.urlopen(req, timeout=400) as r:
                    return json.loads(r.read().decode("utf-8"))
            except Exception as e:  # noqa: BLE001 - research script, retry anything
                last = e
                print(f"{url} attempt {attempt + 1} failed: {e}", file=sys.stderr)
                time.sleep(30 * (attempt + 1))
    raise SystemExit(f"All Overpass endpoints failed: {last}")


def main():
    data = json.load(open("data.json", encoding="utf-8"))
    passes = [t for t in data["towns"] if t.get("kind") == "pass"]
    out = {}
    for start in range(0, len(passes), 60):
        batch = passes[start:start + 60]
        # One labelled set per pass, so results can be told apart.
        parts = []
        for i, p in enumerate(batch):
            parts.append(f'way(around:{RADIUS},{p["latitude"]},{p["longitude"]})[highway~"^({HIGHWAYS})$"];'
                         f'out tags center qt;'
                         f'node(around:1,{p["latitude"]},{p["longitude"]})->.marker{i};'
                         f'make sep pass="{p["key"]}";out;')
        result = fetch("[out:json][timeout:300];" + "".join(parts))
        current = None
        for el in result.get("elements", []):
            if el["type"] == "sep":
                current = el["tags"]["pass"]
                out[current] = list(pending)
                pending.clear()
                continue
            c = el.get("center", {})
            pending.append({"tags": el.get("tags", {}), "lat": c.get("lat"), "lon": c.get("lon")})
        print("passes done:", min(start + 60, len(passes)))
        time.sleep(10)
    os.makedirs("out", exist_ok=True)
    json.dump(out, open("out/osm_roads_at_passes.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("passes with roads:", sum(1 for v in out.values() if v), "of", len(passes))


pending = []

if __name__ == "__main__":
    main()
