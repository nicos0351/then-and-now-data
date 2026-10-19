"""Data version 6: renames found by comparing with an outside list (19 Oct 2026).

Run once:  python tools/data_v6.py data.json
Every change is checked against the official gazette list (PMG question NW959)
or a news report of the gazette; sources are in each entry.
"""
import json
import sys

path = sys.argv[1]
data = json.load(open(path, encoding="utf-8"))
towns = data["towns"]
stories = data["stories"]
by_old = {t["oldName"]: t for t in towns}
by_name = {t["name"]: t for t in towns}

PMG = "https://pmg.org.za/committee-question/16041/"


def key(name, lat, lon):
    return f"asset:{name.lower()}:{lat:.3f}:{lon:.3f}"


# 1. Years taken from the official gazette dates.
YEARS = {
    "Pietersburg": 2002, "Potgietersrus": 2002, "Messina": 2002, "Dendron": 2002,
    "Umtata": 2006, "Engcobo": 2006, "Idutywa": 2006, "Bisho": 2006, "Kentane": 2006, "Nqamakwe": 2006,
    "Duiwelskloof": 2006, "Stanger": 2006,
    "Amanzimtoti": 2010, "Umdloti": 2010, "Mkuze": 2011, "Umzinto": 2013,
}
for old, year in YEARS.items():
    t = by_old[old]
    assert t["hasKnownRename"], old
    t["renamedYear"] = year
    t["source"] = PMG

# 2. Official spelling Bela-Bela (the story's name must match).
t = by_name["Bela Bela"]
t["name"] = "Bela-Bela"
for s in stories:
    if s["key"] == t["key"]:
        s["name"] = "Bela-Bela"

# 3. Louis Trichardt: the full story.
t = by_old["Louis Trichardt"]
t["renamedYear"] = 2014
t["notes"] = ("Renamed Makhado in 2003; the Supreme Court of Appeal set this aside in 2007. It was renamed "
              "Makhado again in 2011, and the High Court set that aside in 2014, so its official name is "
              "Louis Trichardt.")
t["source"] = "https://www.iol.co.za/news/public-to-have-say-in-makhado-name-change-1773802"

# 4. Melmoth is already on the map.
t = by_old["Melmoth"]
t.update(name="eMthonjaneni", hasKnownRename=True, renamedYear=2017, source=PMG)

# 5a. Towns already on the map under their new name, without the old name recorded.
ALREADY_NEW = [
    # new, old, year, source
    ("Mamafubedu", "Petrus Steyn", 2012, PMG),
    ("Hlohlolwane", "Clocolan", 2015, PMG),
    ("Winnie Mandela", "Brandfort", 2021,
     "https://www.timeslive.co.za/politics/2021-08-06-free-state-town-of-brandfort-renamed-winnie-mandela/"),
    ("Tlokoeng", "Mount Fletcher", 2022, "https://businesstech.co.za/news/?p=569096"),
    ("Solomon Linda", "Pomeroy", 2022, "https://businesstech.co.za/news/?p=620143"),
]
for new, old, year, src in ALREADY_NEW:
    t = by_name[new]
    assert not t["hasKnownRename"] and old not in by_old, new
    t.update(oldName=old, hasKnownRename=True, renamedYear=year, source=src)

# 5b. Towns that weren't on the map yet.
NEW = [
    # old, new, province, lat, lon, population, year, notes, source
    ("Morgan's Bay", "Gxarha", "Eastern Cape", -32.704, 28.336, 321, 2022, None,
     "https://businesstech.co.za/news/?p=620143"),
    ("Adendorp", "Bishop Limba", "Eastern Cape", -32.303, 24.547, 401, 2026,
     "Gazetted 6 Feb 2026 with the other Eastern Cape renames, which are under review after more than "
     "38,000 objections (as of May 2026).",
     "https://businesstech.co.za/news/government/850166/east-london-and-graaff-reinet-are-officially-no-more/"),
]
existing = {t["key"] for t in towns}
for old, new, prov, lat, lon, pop, year, notes, src in NEW:
    assert old not in by_old and new not in by_name, old
    k = key(old, lat, lon)
    assert k not in existing, k
    towns.append({
        "key": k, "name": new, "oldName": old, "hasKnownRename": True, "renamedYear": year,
        "reverted": False, "notes": notes, "province": prov, "latitude": lat, "longitude": lon,
        "population": pop, "source": src,
    })

# 6. Name stories for the new names (pronunciation and origins).
WIKI = "https://en.wikipedia.org/wiki/"
key_of = {t["name"]: t["key"] for t in towns}
NEW_STORIES = [
    ("Mamafubedu", "mah-mah-foo-BEH-doo", [], None,
     "The town was to be called Concordia, but Petrus Paulus Steyn's widow sold the land on condition "
     "that it was named after her late husband.", [WIKI + "Petrus_Steyn"]),
    ("Hlohlolwane", "hloh-hloh-LWAH-neh", ["hl"],
     "From Sesotho words meaning 'get up and fight', after a dispute between the Bakwena and Baphuthi "
     "over a maize harvest.",
     "Clocolan is how newer residents said 'Hlohlolwane'.", [WIKI + "Clocolan"]),
    ("Winnie Mandela", "WIN-ee man-DEH-lah", [],
     "Honours Winnie Madikizela-Mandela, who was banished to the town in 1977. Her house there is now a museum.",
     "Brandfort was named after Johannes Brand, President of the Orange Free State, who visited soon after "
     "the town was founded in 1874.", [WIKI + "Brandfort"]),
    ("Tlokoeng", "tloh-KWENG", [],
     "Sesotho for 'place of the Tlokoa clan'.",
     "Mount Fletcher was named after the nearby mountain, probably after Reverend John Fletcher, a friend "
     "of John Wesley.", [WIKI + "Tlokoeng"]),
    ("Gxarha", "gx·AH-rhah", ["x", "rh"], None,
     "Morgan's Bay was named in 1822 after A. F. Morgan, master of the survey ship Barracouta.",
     [WIKI + "Morgan_Bay"]),
    ("Solomon Linda", "SOL-oh-mon LIN-dah", [],
     "Honours Solomon Linda, the musician born here, a pioneer of isicathamiya choral music.",
     "Pomeroy was named after Sir George Pomeroy Colley, the British commander at the Battle of Majuba "
     "Hill in 1881.", [WIKI + "Pomeroy,_South_Africa"]),
    ("Bishop Limba", "BISH-op LEEM-bah", [], None,
     "Adendorp was named after N. J. Adendorff, who owned the farm and divided it into smallholdings "
     "around 1858.", [WIKI + "Adendorp"]),
    ("eMthonjaneni", "eh-m-toh-njah-NEH-nee", ["m"], None,
     "Melmoth was named after Sir Melmoth Osborn, the British resident commissioner of Zululand.",
     [WIKI + "Melmoth,_South_Africa"]),
]
have = {s["key"] for s in stories}
for name, say, sounds, meaning, former, sources in NEW_STORIES:
    k = key_of[name]
    assert k not in have, name
    stories.append({"key": k, "name": name, "say": say, "sounds": sounds, "meaning": meaning,
                    "formerNameOrigin": former, "sources": sources})

data["dataVersion"] = 6
data["updated"] = "2026-10-19"
data["changes"].append({
    "version": 6,
    "date": "2026-10-19",
    "summary": "Eight more renamed towns (e.g. Brandfort → Winnie Mandela, Mount Fletcher → Tlokoeng, "
               "Melmoth → eMthonjaneni), rename years corrected to the official gazette dates, the spelling "
               "Bela-Bela, and the full Louis Trichardt story.",
})
json.dump(data, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("towns", len(towns), "renamed", sum(t["hasKnownRename"] for t in towns), "stories", len(stories))
