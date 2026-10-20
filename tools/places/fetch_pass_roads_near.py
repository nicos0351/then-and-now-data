"""Research helper: for every mountain pass in data.json, download the
roads and paths that run through it from OpenStreetMap, so each pass can
say whether it's tarred, gravel or a footpath.

Run by the manual "Research: roads at passes (OpenStreetMap)" workflow.
Small batches of simple Overpass queries; each way is given to the pass
it's nearest to (within 600 m). The output is written after every batch,
so a failure part-way keeps what was found:
out/osm_roads_at_passes.json = {"<pass key>": [{"tags": {...}, "lat": .., "lon": ..}, ...]}

Data (c) OpenStreetMap contributors, ODbL.
"""
import json
import math
import os
import sys
import time
import urllib.parse
import urllib.request

ENDPOINTS = ["https://overpass-api.de/api/interpreter", "https://overpass.kumi.systems/api/interpreter"]
USER_AGENT = "then-and-now-data research (github.com/nicos0351/then-and-now-data)"
RADIUS = 300  # metres around the pass point
BATCH = 25
HIGHWAYS = "motorway|trunk|primary|secondary|tertiary|unclassified|residential|service|track|path|footway|bridleway"


def km(a, b, c, d):
    return math.hypot((a - c) * 111, (b - d) * 111 * math.cos(math.radians(a)))


def fetch(query):
    data = urllib.parse.urlencode({"data": query}).encode()
    last = None
    for attempt in range(4):
        url = ENDPOINTS[attempt % len(ENDPOINTS)]
        try:
            req = urllib.request.Request(url, data=data, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=240) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:  # noqa: BLE001 - research script, retry anything
            last = e
            print(f"{url} attempt {attempt + 1} failed: {e}", file=sys.stderr, flush=True)
            time.sleep(20 * (attempt + 1))
    print(f"giving up on this batch: {last}", file=sys.stderr, flush=True)
    return None


def main():
    data = json.load(open("data.json", encoding="utf-8"))
    passes = [t for t in data["towns"] if t.get("kind") == "pass"]
    os.makedirs("out", exist_ok=True)
    out = {}
    for start in range(0, len(passes), BATCH):
        batch = passes[start:start + BATCH]
        body = "".join(f'way(around:{RADIUS},{p["latitude"]},{p["longitude"]})[highway~"^({HIGHWAYS})$"];'
                       for p in batch)
        result = fetch(f"[out:json][timeout:200];({body});out tags center qt;")
        if result is not None:
            for p in batch:
                out.setdefault(p["key"], [])
            for el in result.get("elements", []):
                c = el.get("center")
                if not c:
                    continue
                near = min(batch, key=lambda p: km(c["lat"], c["lon"], p["latitude"], p["longitude"]))
                if km(c["lat"], c["lon"], near["latitude"], near["longitude"]) <= 0.6 + RADIUS / 1000:
                    out[near["key"]].append({"tags": el.get("tags", {}), "lat": c["lat"], "lon": c["lon"]})
        json.dump(out, open("out/osm_roads_at_passes.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print("passes done:", min(start + BATCH, len(passes)), "with roads:", sum(1 for v in out.values() if v),
              flush=True)
        time.sleep(5)


if __name__ == "__main__":
    main()
