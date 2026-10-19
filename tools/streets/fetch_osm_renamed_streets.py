"""Research helper: download South African streets that OpenStreetMap
records with a previous name (old_name and similar tags).

Run by the manual "Research: renamed streets (OpenStreetMap)" workflow.
It makes ONE query to the public Overpass API (be gentle: don't schedule
this), and writes:
  out/osm_renamed_streets.json  - one record per street segment
  out/osm_renamed_streets.csv   - the same, for spreadsheets

Data (c) OpenStreetMap contributors, ODbL.
"""
import csv
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

# Every named road/path in South Africa that has any old_name-style tag.
QUERY = """
[out:json][timeout:600];
area["ISO3166-1"="ZA"][admin_level=2]->.za;
(
  way(area.za)[highway][name][~"^(old_name|old_name:.*|was:name|name:old)$"~"."];
);
out tags center;
"""

USER_AGENT = "then-and-now-data research (github.com/nicos0351/then-and-now-data)"


def fetch():
    data = urllib.parse.urlencode({"data": QUERY}).encode()
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
    result = fetch()
    rows = []
    for el in result.get("elements", []):
        tags = el.get("tags", {})
        old = {k: v for k, v in tags.items() if k.startswith("old_name") or k in ("was:name", "name:old")}
        center = el.get("center", {})
        rows.append({
            "osm_id": el.get("id"),
            "name": tags.get("name", ""),
            "old": old,
            "highway": tags.get("highway", ""),
            "lat": center.get("lat"),
            "lon": center.get("lon"),
            "start_date": tags.get("name:start_date", "") or tags.get("start_date", ""),
            "note": tags.get("note", ""),
        })
    os.makedirs("out", exist_ok=True)
    with open("out/osm_renamed_streets.json", "w", encoding="utf-8") as f:
        json.dump({"timestamp": result.get("osm3s", {}).get("timestamp_osm_base"), "streets": rows}, f, ensure_ascii=False, indent=1)
    with open("out/osm_renamed_streets.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["osm_id", "name", "old_names", "highway", "lat", "lon", "name_start_date"])
        for r in rows:
            w.writerow([r["osm_id"], r["name"], " | ".join(f"{k}={v}" for k, v in r["old"].items()), r["highway"], r["lat"], r["lon"], r["start_date"]])
    print(f"{len(rows)} street segments with a previous-name tag")


if __name__ == "__main__":
    main()
