import json, re, math, difflib, collections, sys

streets = json.load(open(sys.argv[1]))['streets']
towns = json.load(open(sys.argv[2]))
towns = [t for t in towns if t.get('kind', 'town') == 'town']

# Metro areas (rough boxes: south, west, north, east) so suburbs count with their city.
METROS = {
    'Durban (eThekwini)': (-30.15, 30.70, -29.55, 31.15),
    'Pretoria (Tshwane)': (-26.00, 27.95, -25.35, 28.70),
    'Johannesburg': (-26.45, 27.75, -25.90, 28.25),
    'Ekurhuleni (East Rand)': (-26.45, 28.15, -25.95, 28.60),
    'Cape Town': (-34.30, 18.30, -33.45, 18.95),
    'Gqeberha (Nelson Mandela Bay)': (-34.10, 25.30, -33.70, 25.75),
    'East London (Buffalo City)': (-33.10, 27.70, -32.85, 28.00),
    'Bloemfontein (Mangaung)': (-29.25, 26.05, -29.00, 26.35),
    'Pietermaritzburg (Msunduzi)': (-29.70, 30.25, -29.50, 30.50),
    'Polokwane': (-23.98, 29.35, -23.82, 29.58),
    'Mbombela': (-25.55, 30.88, -25.38, 31.10),
}

def metro(lat, lon):
    for name, (s, w, n, e) in METROS.items():
        if s <= lat <= n and w <= lon <= e:
            return name
    return None

def dist(a, b, c, d):
    return math.hypot((a - c) * 111, (b - d) * 111 * math.cos(math.radians(a)))

def nearest_town(lat, lon):
    best = min(towns, key=lambda t: dist(lat, lon, t['latitude'], t['longitude']))
    return best['name'], dist(lat, lon, best['latitude'], best['longitude'])

SUFFIX = r'\b(street|st|road|rd|avenue|ave|drive|dr|lane|ln|crescent|cres|close|way|place|pl|boulevard|blvd|highway|hwy|straat|str|weg|laan|rylaan|singel|steeg|plein|terrace|circle|square|extension|ext|freeway|parkway|route|main)\b'

def norm(s):
    s = s.lower()
    s = re.sub(SUFFIX, ' ', s)
    s = re.sub(r'[^a-z0-9 ]', ' ', s)
    return re.sub(r'\s+', ' ', s).strip()

TRANSLATE = {'kerk': 'church', 'stasie': 'station', 'hoof': 'main', 'mark': 'market', 'skool': 'school', 'brug': 'bridge',
             'kerkstraat': 'church', 'van': 'van'}

def classify(new, old):
    a, b = norm(new), norm(old)
    if not a or not b:
        return 'variant'
    if a == b:
        return 'variant'
    r = difflib.SequenceMatcher(None, a.replace(' ', ''), b.replace(' ', '')).ratio()
    if r >= 0.8:
        return 'variant'
    # Afrikaans/English pairs such as Kerkstraat / Church Street
    ta = ' '.join(TRANSLATE.get(w, w) for w in a.split())
    tb = ' '.join(TRANSLATE.get(w, w) for w in b.split())
    if ta == tb:
        return 'translation'
    return 'rename'

rows = []
for s in streets:
    if s['lat'] is None:
        continue
    for k, v in s['old'].items():
        if 'wikidata' in k:
            continue
        for old in v.split(';'):
            old = old.strip()
            if not old:
                continue
            kind = classify(s['name'], old)
            town, km = nearest_town(s['lat'], s['lon'])
            rows.append(dict(name=s['name'], old=old, kind=kind, town=town, km=round(km, 1),
                             metro=metro(s['lat'], s['lon']) or town, lat=s['lat'], lon=s['lon'], highway=s['highway'], key=k))

# One entry per (place, current name, old name)
uniq = {}
for r in rows:
    k = (r['metro'], r['name'], r['old'])
    if k not in uniq:
        uniq[k] = dict(r, segments=1)
    else:
        uniq[k]['segments'] += 1
items = list(uniq.values())
json.dump(items, open('streets_unique.json', 'w'), ensure_ascii=False, indent=1)

kinds = collections.Counter(i['kind'] for i in items)
print('unique street pairs:', len(items), dict(kinds))
ren = [i for i in items if i['kind'] == 'rename']
by = collections.Counter(i['metro'] for i in ren)
print('\nreal renames per place (top 40):')
for p, n in by.most_common(40):
    print(f'{n:5d}  {p}')
print('\nplaces with at least 1 rename:', len(by), ' with >=5:', sum(1 for v in by.values() if v >= 5), ' with >=20:', sum(1 for v in by.values() if v >= 20))
