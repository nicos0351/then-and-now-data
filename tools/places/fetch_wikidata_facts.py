"""Research helper: download facts about South Africa's airports, dams and
mountain passes from Wikidata (data is CC0, free to use with no conditions).

Run by the manual "Research: facts for airports, dams and passes
(Wikidata)" workflow. Three queries to the Wikidata Query Service; writes
out/wikidata_<kind>.json.
"""
import json
import os
import sys
import time
import urllib.parse
import urllib.request

ENDPOINT = "https://query.wikidata.org/sparql"
USER_AGENT = "then-and-now-data research (github.com/nicos0351/then-and-now-data)"

# A quantity with its unit, e.g. "1694|metre".
def q(prop, var):
    return f"""
  OPTIONAL {{ ?item p:{prop}/psv:{prop} ?{var}N . ?{var}N wikibase:quantityAmount ?{var}A .
             OPTIONAL {{ ?{var}N wikibase:quantityUnit ?{var}U . ?{var}U rdfs:label ?{var}UL . FILTER(LANG(?{var}UL) = "en") }} }}"""


def label(prop, var):
    return f"""
  OPTIONAL {{ ?item wdt:{prop} ?{var}I . ?{var}I rdfs:label ?{var} . FILTER(LANG(?{var}) = "en") }}"""


def plain(prop, var):
    return f"\n  OPTIONAL {{ ?item wdt:{prop} ?{var} . }}"


def query(classes, fields):
    select = " ".join(
        f"(SAMPLE(?{v}) AS ?{v})" if kind != "q" else f"(SAMPLE(?{v}A) AS ?{v}) (SAMPLE(?{v}UL) AS ?{v}Unit)"
        for kind, _, v in fields)
    body = "".join(q(p, v) if k == "q" else label(p, v) if k == "label" else plain(p, v) for k, p, v in fields)
    values = " ".join(f"wd:{c}" for c in classes)
    return f"""
SELECT ?item (SAMPLE(?name) AS ?name) (SAMPLE(?coord) AS ?coord) (SAMPLE(?enwiki) AS ?enwiki) {select} WHERE {{
  VALUES ?class {{ {values} }}
  ?item wdt:P17 wd:Q258 ; wdt:P31/wdt:P279* ?class .
  OPTIONAL {{ ?item rdfs:label ?name . FILTER(LANG(?name) = "en") }}
  OPTIONAL {{ ?item wdt:P625 ?coord . }}
  OPTIONAL {{ ?enwiki schema:about ?item ; schema:isPartOf <https://en.wikipedia.org/> . }}{body}
}} GROUP BY ?item
"""


KINDS = {
    "airports": (["Q1248784"], [
        ("plain", "P239", "icao"), ("plain", "P238", "iata"), ("q", "P2044", "elevation"),
        ("plain", "P1619", "opened"), ("plain", "P571", "inception"), ("label", "P137", "operator"),
        ("label", "P131", "place"), ("plain", "P856", "website"),
    ]),
    "dams": (["Q12323", "Q131681"], [
        ("label", "P206", "river"), ("q", "P2048", "height"), ("q", "P2043", "length"),
        ("q", "P2234", "volume"), ("q", "P2046", "area"), ("plain", "P571", "inception"),
        ("plain", "P1619", "opened"), ("plain", "P729", "service"), ("label", "P137", "operator"),
        ("label", "P127", "owner"), ("label", "P31", "type"), ("plain", "P402", "osm"),
    ]),
    "passes": (["Q133056"], [
        ("q", "P2044", "elevation"), ("label", "P131", "place"), ("label", "P4552", "range"),
    ]),
}


def fetch(sparql):
    data = urllib.parse.urlencode({"query": sparql, "format": "json"}).encode()
    last = None
    for attempt in range(4):
        try:
            req = urllib.request.Request(ENDPOINT, data=data, headers={
                "User-Agent": USER_AGENT, "Accept": "application/sparql-results+json"})
            with urllib.request.urlopen(req, timeout=300) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:  # noqa: BLE001 - research script, retry anything
            last = e
            print(f"attempt {attempt + 1} failed: {e}", file=sys.stderr)
            time.sleep(30 * (attempt + 1))
    raise SystemExit(f"Wikidata query failed: {last}")


def main():
    os.makedirs("out", exist_ok=True)
    for kind, (classes, fields) in KINDS.items():
        result = fetch(query(classes, fields))
        rows = []
        for b in result["results"]["bindings"]:
            rows.append({k: v["value"] for k, v in b.items()})
        json.dump({"source": "Wikidata (CC0)", kind: rows}, open(f"out/wikidata_{kind}.json", "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
        print(kind, len(rows))
        time.sleep(10)


if __name__ == "__main__":
    main()
