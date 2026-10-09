"""Checks offline/packs.json - the list of Offline Maps packs the app offers.

Run:  python validate_packs.py offline/packs.json

The app does the same checks (OfflinePack.parseIndex) and ignores a list
that fails them, but catching mistakes here keeps a broken list from ever
being published. The .mbtiles files themselves live on GitHub Releases,
not in this repository.
"""
import json
import re
import sys

ID = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")


def main(path):
    errors = []
    try:
        data = json.load(open(path, encoding="utf-8"))
    except (OSError, ValueError) as e:
        sys.exit(f"{path}: not valid JSON ({e})")
    if not isinstance(data, dict) or data.get("format") != 1 or not isinstance(data.get("packs"), list):
        sys.exit(f'{path}: must be {{"format": 1, "packs": [...]}}')
    seen = set()
    for i, p in enumerate(data["packs"]):
        where = f"pack {i + 1}"
        if not isinstance(p, dict):
            errors.append(f"{where}: must be an object")
            continue
        pid = p.get("id")
        if not isinstance(pid, str) or not ID.match(pid):
            errors.append(f"{where}: id must be lower case letters, digits and dashes")
        elif pid in seen:
            errors.append(f"{where}: duplicate id {pid}")
        seen.add(pid)
        where = f"pack {pid or i + 1}"
        if not str(p.get("url", "")).startswith("https://"):
            errors.append(f"{where}: url must start with https://")
        if not isinstance(p.get("sizeBytes"), int) or p["sizeBytes"] <= 0:
            errors.append(f"{where}: sizeBytes must be the exact file size in bytes")
        lo, hi = p.get("minZoom"), p.get("maxZoom")
        if not (isinstance(lo, int) and isinstance(hi, int) and 0 <= lo <= hi <= 20):
            errors.append(f"{where}: minZoom/maxZoom must be whole numbers with 0 <= minZoom <= maxZoom <= 20")
        if not isinstance(p.get("version", 1), int) or p.get("version", 1) < 1:
            errors.append(f"{where}: version must be a whole number, 1 or more")
        if not p.get("name") or not p.get("attribution"):
            errors.append(f"{where}: needs a name and an attribution (map data credit)")
        b = p.get("bounds")
        if b is not None:
            ok = isinstance(b, list) and len(b) == 4 and all(isinstance(x, (int, float)) for x in b)
            if not ok or not (b[0] < b[2] and b[1] < b[3]):
                errors.append(f"{where}: bounds must be [west, south, east, north]")
    if errors:
        sys.exit("\n".join(errors))
    print(f"{path}: OK, {len(data['packs'])} pack(s)")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "offline/packs.json")
