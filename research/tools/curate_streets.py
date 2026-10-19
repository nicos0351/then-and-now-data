"""Curate the OSM street-rename pairs into a reviewable list.

Input: streets_unique.json (from analyse_streets.py). Output: streets_curated.json
Each row: area, town, old, new, status (Keep/Check/Drop/Add), note, source, lat, lon, segments, road_type.
"""
import json
import sys
from collections import OrderedDict

rows = [r for r in json.load(open(sys.argv[1])) if r['kind'] == 'rename']

# Canonical spellings, so the same rename isn't listed twice.
NEW_CANON = {
    'Nelson Mandela Blvd': 'Nelson Mandela Boulevard',
    'Peter Mokaba Ridge': 'Peter Mokaba Road',
    'Chief Albert Luthuli Drive': 'Albert Luthuli Drive',
    'Es\'kia Mphahlele Drive West': 'Es\'kia Mphahlele Drive',
    'Steve Biko Street': 'Steve Biko Road',
    'Curnick Ndlovu': 'Curnick Ndlovu Highway',
}
OLD_CANON = {
    'Keizersgracht Road': 'Keizersgracht',
    'D.F. Malan Drive': 'DF Malan Drive',
    'Jacob Mare': 'Jacob Mare Street',
    'Francoise Road': 'Francois Road',
    'Krugerstraat': 'Kruger Street',
    'Van Riebeeck-straat': 'Van Riebeeck Street',
    'Tomstraat': 'Tom Street',
    'Van der Hoff-weg': 'Van der Hoff Road',
    'Kerkstraat': 'Kerk Street',
    'Kerk Straat': 'Church Street',
    'Modderdam East-West Road': 'Modderdam Road',
}
AREA_CANON = {'Mpophomeni': 'Pietermaritzburg (Msunduzi)', 'Diepsloot': 'Johannesburg'}

# (old, new) pairs that are mapping noise, numbered placeholder streets, paths,
# translations or small local changes that aren't worth showing.
DROP = {
    ('Western Boulevard', 'Beach Road'): 'Mapping detail: only a short joining segment',
    ('Western Boulevard', 'Hans Strijdom Avenue'): 'Mapping detail: only a short joining segment',
    ('Goede Gift Road', 'Flagship Way'): 'A flight of steps, not a street',
    ('De Waal Drive Service Road', 'Service Road'): 'Service road, not a rename',
    ('Lansdowne Road', 'Palmyra Road'): 'Mapping detail: only a short joining segment',
    ('Alexandra Street', 'Protea Street'): 'Small local change',
    ('Zone 5 Road', 'Washington Drive'): 'Township zone number replaced by a name',
    ('Zone 16 Road', 'Washington Drive'): 'Township zone number replaced by a name',
    ('106398 Street', 'Curnick Ndlovu Highway'): 'Numbered placeholder street',
    ('121915 Street', 'Frosthaven Close'): 'Numbered placeholder street',
    ('121587 Street', 'Honeyhaven Close'): 'Numbered placeholder street',
    ('121586 Street', 'Kingshaven Place'): 'Numbered placeholder street',
    ('121377 Street', 'Silverbrook Road'): 'Numbered placeholder street',
    ('King Edward Street', '1st Avenue'): 'Small local change',
    ('Dan Pienaar Street', 'Link Road'): 'Small local change',
    ('Union Road', 'Villiers Road'): 'Small local change',
    ('Flat Rock Pass', 'Donkey Pass'): 'A farm track, not a street',
    ('Spoorwegstraat', 'Voortrekker Street'): 'Small local change',
    ('Rooth Street', '12th Avenue'): 'Mapping detail: only a short joining segment',
    ('Johan Avenue', '5th Street'): 'Small local change',
    ('Marjorie Street', 'Fig Place Road'): 'Service road, small local change',
    ('Old Potchefstroom Road', 'Klipspruit Valley Road'): 'Bus lane segment only',
    ('Old Toll Road', 'Milkwood Drive'): 'Small local change',
    ('Edendale Road', 'Pine Street North'): 'Mapping detail: only a short joining segment',
    ('Slangspruit Road', 'Pentrich Road'): 'Mapping detail: only a short joining segment',
    ('Richmond Road', 'Alexandra Road'): 'Mapping detail: only a short joining segment',
    ('Prinsloo Street', 'Bloed Street'): 'Mapping detail: only a short joining segment',
    ('Prinsloo Street', 'Soutpansberg Road'): 'Mapping detail: only a short joining segment',
    ('Church Street', 'Cussonia Avenue'): 'Mapping detail: only a short joining segment',
    ('Mears Street', 'Elandspoort Avenue'): 'Mapping detail: only a short joining segment',
    ('Jeppe Street', 'Steve Biko Road'): 'Mapping detail: only a short joining segment',
    ('Mitchell Street', 'Nana Sita Street'): 'Mapping detail: only a short joining segment',
    ('Hans Strijdom Drive', 'Trichardt Road'): 'Mapping detail: only a short joining segment',
    ('Hornbill', 'Korhaan Street'): 'Translation (both mean hornbill-type birds), small local street',
    ('Striptease Trail', 'River Trail'): 'A hiking path, not a street',
    ('Willow Road', 'Wilger'): 'Translation (wilger = willow)',
    ('Express', 'Voortrekker Street'): 'Small local change',
    ('Kweek', 'Struik Street'): 'Small local change',
    ('Haldon Road', 'Bell Street'): 'Mapping detail: only a short joining segment',
    ('Pasteur Drive', 'Van Rippen Crescent'): 'Small local change',
    ('Canal Road', 'Richard Walne Road'): 'Service road, small local change',
    ('Maxwell Drive', 'Van der Bijl Avenue'): 'Small local change in an office park',
}

# Plausible, but should be confirmed against the council's list before release.
CHECK = {
    ('Justice Street', 'Rabbi Mirvish Avenue'): 'Short street; confirm with City of Cape Town',
    ('Ring Road', 'Madiba Circle'): 'Campus/service road; confirm',
    ('Berea Road', 'Chris Ntuli Road'): 'Only 2 segments; the main Berea Road became King Dinuzulu Road',
    ('Albert Street', 'Ingcuce Road'): 'Confirm against eThekwini list',
    ('Bruce-Bays Bridge', 'Buffalo Bridge'): 'A bridge; confirm with Buffalo City',
    ('Langenhoven Street', 'Pasteur Boulevard'): 'Unusual pair; confirm with Emfuleni',
    ('Voortrekker Rd', 'Aerodrome Road'): 'Single segment; confirm with Mahikeng',
    ('Prince Mangasuthu Buthelezi', 'Pine Street'): 'Looks like a rename that was reversed; confirm',
    ('Albert', 'Nelson Mandela Boulevard'): 'Old name looks incomplete in the map data',
    ('Durban Road', 'Alan Paton Avenue'): 'Older rename (before 1994?); confirm the year',
    ('Pietersen Street', 'Promosa Road'): 'Single segment; confirm with JB Marks',
    ('Curlewis Street', 'Ikageng Street'): 'Confirm with JB Marks',
    ('Stasie Road', 'Piet Bosman Street'): 'Confirm with JB Marks',
    ('Haldon Road', 'Walter Sisulu Road'): 'Confirm with Mangaung',
    ('3rd Avenue', 'Josiah Mathebula Street'): 'Single segment; confirm',
}

merged = OrderedDict()
for r in rows:
    new = NEW_CANON.get(r['name'], r['name'])
    old = OLD_CANON.get(r['old'], r['old'])
    area = AREA_CANON.get(r['town'], r['metro'] or r['town'])
    key = (area, old, new)
    m = merged.setdefault(key, {'town': r['town'], 'segments': 0, 'spellings': set(), '_best': -1})
    m['segments'] += r['segments']
    m['spellings'].update({r['old'], r['name']} - {old, new})
    # Position and road type come from the longest stretch.
    if r['segments'] > m['_best']:
        m.update(_best=r['segments'], town=r['town'], lat=round(r['lat'], 5), lon=round(r['lon'], 5),
                 road_type=r['highway'])

out = []
for (area, old, new), m in merged.items():
    if (old, new) in DROP:
        status, note = 'Drop', DROP[(old, new)]
    elif (old, new) in CHECK:
        status, note = 'Check', CHECK[(old, new)]
    else:
        status, note = 'Keep', ''
    if m['spellings']:
        extra = 'Also mapped as: ' + ', '.join(sorted(m['spellings']))
        note = f'{note}. {extra}' if note else extra
    out.append({
        'area': area, 'town': m['town'], 'old': old, 'new': new, 'status': status, 'note': note,
        'source': 'OpenStreetMap', 'lat': m['lat'], 'lon': m['lon'],
        'segments': m['segments'], 'road_type': m['road_type'],
    })

# Officially announced renames that the map data doesn't have yet.
ADD = [
    ('Johannesburg', 'Johannesburg', 'Bree Street', 'Lilian Ngoyi Street', 'Inner-city rename adopted 4 Sept 2014'),
    ('Johannesburg', 'Johannesburg', 'Jeppe Street', 'Rahima Moosa Street', 'Inner-city rename adopted 4 Sept 2014'),
    ('Johannesburg', 'Johannesburg', 'President Street', 'Helen Joseph Street', 'Inner-city rename adopted 4 Sept 2014'),
    ('Johannesburg', 'Johannesburg', 'Noord Street', 'Sophie de Bruyn Street', 'Inner-city rename adopted 4 Sept 2014'),
    ('Johannesburg', 'Johannesburg', 'Sauer Street', 'Pixley Seme Street', 'Inner-city rename, 2015'),
    ('Johannesburg', 'Newclare', 'Mayor Street', 'Rahima Moosa Avenue', 'Renamed 2007'),
    ('Pretoria (Tshwane)', 'Pretoria', 'Lucas Mangope Highway', 'Molefe Makinta Highway', 'On Tshwane\'s 2012 list of 28'),
    ('Pretoria (Tshwane)', 'Pretoria', 'Leah Mangope Road', 'Peter Magano Road', 'On Tshwane\'s 2012 list of 28'),
    ('Ekurhuleni (East Rand)', 'Ekurhuleni', 'Tom Jones Road', 'Amina Cachalia', 'On Ekurhuleni\'s list of 44 (approved 2019, signs going up from 2021); street type not given in the list'),
    ('Ekurhuleni (East Rand)', 'Ekurhuleni', 'Voortrekker Road, Kempton Park', 'Amon Ngulele', 'On Ekurhuleni\'s list of 44 (approved 2019, signs going up from 2021); street type not given in the list'),
    ('Ekurhuleni (East Rand)', 'Ekurhuleni', 'Rietfontein Road', 'Chris Dlamini', 'On Ekurhuleni\'s list of 44 (approved 2019, signs going up from 2021); street type not given in the list'),
    ('Ekurhuleni (East Rand)', 'Ekurhuleni', 'Putfontein Road', 'Cleoupas Nsibanda', 'On Ekurhuleni\'s list of 44 (approved 2019, signs going up from 2021); street type not given in the list'),
    ('Ekurhuleni (East Rand)', 'Ekurhuleni', 'Tonk Meter Road', 'Congress Skhumbuzo Mtsweni', 'On Ekurhuleni\'s list of 44 (approved 2019, signs going up from 2021); street type not given in the list'),
    ('Ekurhuleni (East Rand)', 'Ekurhuleni', 'Heidelberg Road', 'David Bopape', 'On Ekurhuleni\'s list of 44 (approved 2019, signs going up from 2021); street type not given in the list'),
    ('Ekurhuleni (East Rand)', 'Ekurhuleni', 'Swartkoppies Road', 'Ali Maziya', 'On Ekurhuleni\'s list of 44 (approved 2019, signs going up from 2021); street type not given in the list'),
    ('Ekurhuleni (East Rand)', 'Ekurhuleni', 'Barry Marais Road', 'George Makhubela', 'On Ekurhuleni\'s list of 44 (approved 2019, signs going up from 2021); street type not given in the list'),
    ('Ekurhuleni (East Rand)', 'Ekurhuleni', 'Osborne Road', 'Johnson Nonjeke', 'On Ekurhuleni\'s list of 44 (approved 2019, signs going up from 2021); street type not given in the list'),
    ('Ekurhuleni (East Rand)', 'Ekurhuleni', 'Griffiths Road', 'Joseph Tate Kagarose', 'On Ekurhuleni\'s list of 44 (approved 2019, signs going up from 2021); street type not given in the list'),
    ('Ekurhuleni (East Rand)', 'Ekurhuleni', 'Denne Road / Goods Road', 'Kunyamane Ranyaoa', 'On Ekurhuleni\'s list of 44 (approved 2019, signs going up from 2021); street type not given in the list'),
    ('Ekurhuleni (East Rand)', 'Ekurhuleni', 'Barbara Road', 'Lazarus Mawela', 'On Ekurhuleni\'s list of 44 (approved 2019, signs going up from 2021); street type not given in the list'),
    ('Ekurhuleni (East Rand)', 'Ekurhuleni', 'Linksfield Road', 'Lethabo Malatjie', 'On Ekurhuleni\'s list of 44 (approved 2019, signs going up from 2021); street type not given in the list'),
    ('Ekurhuleni (East Rand)', 'Ekurhuleni', 'Ergo Road / Eleventh Road', 'Margaret Gazo', 'On Ekurhuleni\'s list of 44 (approved 2019, signs going up from 2021); street type not given in the list'),
    ('Ekurhuleni (East Rand)', 'Ekurhuleni', 'Snake Road', 'Mary Moodley', 'On Ekurhuleni\'s list of 44 (approved 2019, signs going up from 2021); street type not given in the list'),
    ('Ekurhuleni (East Rand)', 'Ekurhuleni', 'Michelle Avenue, Meyersdal', 'Nelson Mandela', 'On Ekurhuleni\'s list of 44 (approved 2019, signs going up from 2021); street type not given in the list'),
    ('Ekurhuleni (East Rand)', 'Ekurhuleni', 'Nigel Road / Wit Road', 'Ngungunyane Mashabane', 'On Ekurhuleni\'s list of 44 (approved 2019, signs going up from 2021); street type not given in the list'),
    ('Ekurhuleni (East Rand)', 'Ekurhuleni', 'Kraft Road', 'Ntemi Ncwane', 'On Ekurhuleni\'s list of 44 (approved 2019, signs going up from 2021); street type not given in the list'),
    ('Ekurhuleni (East Rand)', 'Ekurhuleni', 'Jones Road', 'Walter Sisulu', 'On Ekurhuleni\'s list of 44 (approved 2019, signs going up from 2021); street type not given in the list'),
    ('Ekurhuleni (East Rand)', 'Ekurhuleni', 'Kingsway Road, Daveyton', 'Richard Mhlongo', 'On Ekurhuleni\'s list of 44 (approved 2019, signs going up from 2021); street type not given in the list'),
    ('Ekurhuleni (East Rand)', 'Ekurhuleni', 'Holfontein Road / Pansy Road', 'Salvation Motshweni', 'On Ekurhuleni\'s list of 44 (approved 2019, signs going up from 2021); street type not given in the list'),
    ('Ekurhuleni (East Rand)', 'Ekurhuleni', 'Kliprivier Road (R550)', 'Sam Ntuli', 'On Ekurhuleni\'s list of 44 (approved 2019, signs going up from 2021); street type not given in the list'),
    ('Ekurhuleni (East Rand)', 'Ekurhuleni', 'Wits Rifles Road', 'Sam Sidu', 'On Ekurhuleni\'s list of 44 (approved 2019, signs going up from 2021); street type not given in the list'),
    ('Ekurhuleni (East Rand)', 'Ekurhuleni', 'Bronkhorstspruit Road', 'Sarah Mnyele', 'On Ekurhuleni\'s list of 44 (approved 2019, signs going up from 2021); street type not given in the list'),
    ('Ekurhuleni (East Rand)', 'Ekurhuleni', 'Jet Park Road', 'Sthembiso Clarence Lukhele', 'On Ekurhuleni\'s list of 44 (approved 2019, signs going up from 2021); street type not given in the list'),
    ('Ekurhuleni (East Rand)', 'Ekurhuleni', 'Van Buuren Road', 'Thabo Mbeki Road', 'On Ekurhuleni\'s list of 44 (approved 2019, signs going up from 2021); street type not given in the list'),
    ('Ekurhuleni (East Rand)', 'Ekurhuleni', 'Rondebult Road, Boksburg', 'Thomas Nkobi', 'On Ekurhuleni\'s list of 44 (approved 2019, signs going up from 2021); street type not given in the list'),
    ('Ekurhuleni (East Rand)', 'Ekurhuleni', 'Grey Avenue', 'Vuyisile Bixa', 'On Ekurhuleni\'s list of 44 (approved 2019, signs going up from 2021); street type not given in the list'),
    ('Ekurhuleni (East Rand)', 'Ekurhuleni', 'Benoni Road', 'Willie Oupa Lukhele', 'On Ekurhuleni\'s list of 44 (approved 2019, signs going up from 2021); street type not given in the list'),
]
for area, town, old, new, note in ADD:
    out.append({
        'area': area, 'town': town, 'old': old, 'new': new, 'status': 'Add',
        'note': note + '; not yet in the map data, position must be added by hand',
        'source': 'Official announcement', 'lat': None, 'lon': None, 'segments': 0, 'road_type': '',
    })

order = {'Keep': 0, 'Add': 1, 'Check': 2, 'Drop': 3}
out.sort(key=lambda r: (r['area'], order[r['status']], r['new']))
json.dump(out, open(sys.argv[2], 'w'), indent=1, ensure_ascii=False)

from collections import Counter
print(Counter(r['status'] for r in out), len(out))
by_area = Counter(r['area'] for r in out if r['status'] in ('Keep', 'Add', 'Check'))
for a, n in by_area.most_common():
    k = sum(1 for r in out if r['area'] == a and r['status'] == 'Keep')
    ad = sum(1 for r in out if r['area'] == a and r['status'] == 'Add')
    c = sum(1 for r in out if r['area'] == a and r['status'] == 'Check')
    print(f'{a:32} keep {k:3} add {ad} check {c}')
