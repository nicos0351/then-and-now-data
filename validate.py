"""Checks data.json before it goes live.

Run:  python validate.py data.json [--base previous-data.json]

The app downloads data.json from GitHub Pages. A broken file can't harm
the app (it re-checks everything and keeps its current data if anything
looks wrong), but this catches mistakes before they're published.
GitHub runs it automatically on every pull request and every push to main.
"""
import json
import sys

PROVINCES = {
    "Eastern Cape", "Free State", "Gauteng", "KwaZulu-Natal", "Limpopo",
    "Mpumalanga", "North West", "Northern Cape", "Western Cape",
}
KINDS = {"town", "airport", "dam", "pass"}   # the app ignores files with other kinds
MIN_TOWNS = 900          # the app refuses files with fewer towns than this
FORMAT = 1               # bump only together with an app release that understands the new format
SOUND_CODES = {"c", "q", "x", "gc", "gq", "nc", "nq", "nx", "ngc", "ngq", "rh", "hl", "dl",
               "bh", "ty", "kg", "g_sotho", "aspirated", "m"}

errors = []
warnings = []


def err(msg):
    errors.append(msg)


def check(path, base_path=None):
    try:
        data = json.load(open(path, encoding="utf-8"))
    except Exception as e:  # noqa: BLE001
        err(f"data.json is not valid JSON: {e}")
        return

    if data.get("format") != FORMAT:
        err(f"format must be {FORMAT}")
    version = data.get("dataVersion")
    if not isinstance(version, int) or version < 1:
        err("dataVersion must be a whole number")
    if not isinstance(data.get("updated"), str):
        err('updated must be a date like "2026-10-09"')
    changes = data.get("changes")
    if not isinstance(changes, list) or not any(c.get("version") == version for c in changes):
        err("changes must include an entry for the current dataVersion, saying what changed")

    towns = data.get("towns")
    if not isinstance(towns, list) or len(towns) < MIN_TOWNS:
        err(f"towns must be a list of at least {MIN_TOWNS} towns")
        return

    keys = set()
    for i, t in enumerate(towns):
        where = f"town #{i + 1} ({t.get('name', '?')})"
        for field, kind in [("key", str), ("name", str), ("oldName", str), ("hasKnownRename", bool),
                            ("reverted", bool), ("province", str), ("latitude", (int, float)),
                            ("longitude", (int, float)), ("population", int)]:
            if not isinstance(t.get(field), kind):
                err(f"{where}: '{field}' is missing or the wrong type")
        if t.get("kind", "town") not in KINDS:
            err(f"{where}: kind must be one of {sorted(KINDS)} (or left out for a town)")
        if t.get("renamedYear") is not None and not isinstance(t.get("renamedYear"), int):
            err(f"{where}: renamedYear must be a year or null")
        if t.get("notes") is not None and not isinstance(t.get("notes"), str):
            err(f"{where}: notes must be text or null")
        key = t.get("key", "")
        if not str(key).startswith("asset:"):
            err(f"{where}: key must start with 'asset:'")
        if key in keys:
            err(f"{where}: duplicate key {key}")
        keys.add(key)
        if t.get("province") not in PROVINCES:
            err(f"{where}: unknown province '{t.get('province')}'")
        lat, lon = t.get("latitude"), t.get("longitude")
        if isinstance(lat, (int, float)) and isinstance(lon, (int, float)):
            if not (-35.5 < lat < -22 and 16 < lon < 33.5):
                err(f"{where}: coordinates are outside South Africa")
        if not t.get("hasKnownRename") and t.get("oldName") != t.get("name"):
            err(f"{where}: no rename recorded, so oldName must equal name")
        year = t.get("renamedYear")
        if isinstance(year, int) and not (1900 <= year <= 2100):
            err(f"{where}: renamedYear {year} looks wrong")

    stories = data.get("stories")
    if not isinstance(stories, list):
        err("stories must be a list")
        stories = []
    by_key = {t.get("key"): t for t in towns}
    story_keys = set()
    for s in stories:
        name = s.get("name", "?")
        town = by_key.get(s.get("key"))
        if town is None:
            err(f"story '{name}': key {s.get('key')} doesn't match any town")
            continue
        if town.get("name") != name:
            err(f"story '{name}': name must match the town's current name '{town.get('name')}'")
        story_keys.add(s.get("key"))
        for code in s.get("sounds", []):
            if code not in SOUND_CODES:
                err(f"story '{name}': unknown sound code '{code}' (the app has no tip for it)")
        if (s.get("meaning") or s.get("formerNameOrigin")) and not s.get("sources"):
            err(f"story '{name}': a meaning or old-name origin needs at least one source link")
    for t in towns:
        if t.get("hasKnownRename") and str(t.get("oldName", "")).lower() != str(t.get("name", "")).lower():
            if t.get("key") not in story_keys:
                warnings.append(f"{t.get('name')}: renamed, but has no name story yet (optional)")

    if base_path:
        try:
            base = json.load(open(base_path, encoding="utf-8"))
        except Exception:  # noqa: BLE001
            base = None
        if base:
            if json.dumps(base, sort_keys=True) != json.dumps(data, sort_keys=True):
                if not isinstance(version, int) or version <= base.get("dataVersion", 0):
                    err(f"data changed, so dataVersion must go up (it is {version}, was {base.get('dataVersion')})")
            removed = {t["key"] for t in base.get("towns", [])} - keys
            if removed:
                warnings.append(f"{len(removed)} town(s) removed: {sorted(removed)[:10]}")
            if len(removed) > 0.02 * len(base.get("towns", [])):
                err(f"{len(removed)} towns removed - more than 2%. If that's intended, say so in the pull request.")


if __name__ == "__main__":
    args = sys.argv[1:]
    base_arg = None
    if "--base" in args:
        i = args.index("--base")
        base_arg = args[i + 1] if i + 1 < len(args) else None
        args = args[:i] + args[i + 2:]
    check(args[0] if args else "data.json", base_arg)
    for w in warnings:
        print("warning:", w)
    for e in errors:
        print("ERROR:", e)
    if errors:
        print(f"\n{len(errors)} problem(s) found - data.json would be rejected by the app.")
        sys.exit(1)
    print("data.json looks good.")
