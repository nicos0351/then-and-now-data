"""Research helper: what does OpenStreetMap know about electric vehicle
charging stations in South Africa? Decides whether a charging-station layer
in the app is worth building.

Run by the manual "Research: EV charging stations (OpenStreetMap)"
workflow. One Overpass query for amenity=charging_station inside South
Africa. Writes out/charging_osm.json (every station with its useful tags,
data ODbL) and out/summary.md (counts by operator, province, plug type,
power, and how complete the tags are).
"""
import collections
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
USER_AGENT = "then-and-now-data research (github.com/nicos0351/then-and-now-data)"
OVERPASS = ["https://overpass-api.de/api/interpreter", "https://overpass.kumi.systems/api/interpreter"]
QUERY = """[out:json][timeout:300];
area["ISO3166-1"="ZA"][admin_level=2]->.za;
nwr[amenity=charging_station](area.za);
out center tags;"""

outline = json.load(open(os.path.join(HERE, "..", "places", "provinces.json"), encoding="utf-8"))


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
    return "(outside outline)"


def fetch():
    data = urllib.parse.urlencode({"data": QUERY}).encode()
    for attempt in range(6):
        url = OVERPASS[attempt % len(OVERPASS)]
        try:
            req = urllib.request.Request(url, data=data, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=400) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:  # noqa: BLE001
            print(f"retry {attempt + 1} ({url}): {e}", file=sys.stderr)
            time.sleep(30 * (attempt + 1))
    sys.exit("Overpass did not answer")


def kw(value):
    """Largest number of kW in a tag like '50 kW', '22kW;7.4 kW', '150000 W'."""
    best = None
    for part in re.split(r"[;,]", value or ""):
        m = re.search(r"([\d.]+)\s*(kW|kw|KW|W)?", part)
        if not m:
            continue
        try:
            n = float(m.group(1))
        except ValueError:
            continue
        unit = (m.group(2) or "").lower()
        if unit == "w" or (unit == "" and n > 1000):
            n /= 1000
        best = n if best is None else max(best, n)
    return best


DC_SOCKETS = ("type2_combo", "chademo", "ccs", "type1_combo", "gb_dc", "tesla_supercharger", "nacs")


def main():
    res = fetch()
    stations = []
    for e in res.get("elements", []):
        t = e.get("tags", {})
        c = e.get("center") or {"lat": e.get("lat"), "lon": e.get("lon")}
        if c.get("lat") is None:
            continue
        sockets = {k[len("socket:"):]: v for k, v in t.items()
                   if k.startswith("socket:") and k.count(":") == 1}
        outputs = [kw(v) for k, v in t.items() if k.startswith("socket:") and k.endswith(":output")]
        power = max([o for o in outputs if o] + ([kw(t.get("charging_station:output"))] if t.get("charging_station:output") else []), default=None)
        stations.append({
            "osm": f"{e['type']}/{e['id']}",
            "lat": c["lat"], "lon": c["lon"],
            "province": province(c["lat"], c["lon"]),
            "name": t.get("name"),
            "operator": t.get("operator"),
            "network": t.get("network"),
            "brand": t.get("brand"),
            "capacity": t.get("capacity"),
            "sockets": sockets,
            "max_kw": power,
            "dc": any(s.startswith(DC_SOCKETS) for s in sockets) or (power or 0) >= 25,
            "access": t.get("access"),
            "fee": t.get("fee"),
            "opening_hours": t.get("opening_hours"),
            "check_date": t.get("check_date") or t.get("survey:date"),
        })

    os.makedirs("out", exist_ok=True)
    with open("out/charging_osm.json", "w", encoding="utf-8") as f:
        json.dump(stations, f, ensure_ascii=False, indent=1)

    n = len(stations)
    def who(s):
        return (s["network"] or s["operator"] or s["brand"] or "(not tagged)").strip()
    by_who = collections.Counter(who(s) for s in stations)
    by_prov = collections.Counter(s["province"] for s in stations)
    socket_types = collections.Counter(k for s in stations for k in s["sockets"])
    pct = lambda k: f"{100 * sum(1 for s in stations if s[k]) / n:.0f}%" if n else "-"
    lines = [
        f"# EV charging stations in South Africa (OpenStreetMap, {time.strftime('%Y-%m-%d')})", "",
        f"**{n} stations** (amenity=charging_station). DC / fast (CCS, CHAdeMO or 25 kW+): "
        f"{sum(1 for s in stations if s['dc'])}.", "",
        "## How complete the tags are", "",
        f"- name: {pct('name')}", f"- operator: {pct('operator')}", f"- network: {pct('network')}",
        f"- plug types (socket:*): {sum(1 for s in stations if s['sockets']) * 100 // max(n, 1)}%",
        f"- power (kW): {pct('max_kw')}", f"- fee: {pct('fee')}", f"- opening hours: {pct('opening_hours')}",
        f"- access: {pct('access')}", "",
        "## By network / operator", "", "| Network or operator | Stations |", "|---|---|",
        *[f"| {k} | {v} |" for k, v in by_who.most_common(25)], "",
        "## By province", "", "| Province | Stations |", "|---|---|",
        *[f"| {k} | {v} |" for k, v in by_prov.most_common()], "",
        "## Plug types tagged", "", "| Socket | Stations |", "|---|---|",
        *[f"| {k} | {v} |" for k, v in socket_types.most_common()],
    ]
    with open("out/summary.md", "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
