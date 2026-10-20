"""Read saved copies of the Department of Water and Sanitation's weekly
provincial "State of Dams" pages into one JSON file for match_dws.py.

Run:  python tools/places/parse_dws.py <folder of saved pages> <out.json>

Save each page from https://www.dws.gov.za/Hydrology/Weekly/ProvinceWeek.aspx?region=CODE
(codes EC FS G KN LP M NC NW WC) as "Webpage, HTML only", named CODE.html.
"""
import re, sys, json, glob, os
def parse(path):
    s = open(path, encoding='utf-8', errors='replace').read()
    m = re.search(r'([A-Za-z -]+) Provincial State of Dams on (\d{4}-\d{2}-\d{2})', s)
    rows = []
    for tr in re.findall(r'<tr>(.*?)</tr>', s, re.S):
        tds = re.findall(r'<td[^>]*>(.*?)</td>', tr, re.S)
        st = re.search(r'percentile\.aspx\?station=(?:%20|\s)*([A-Z0-9]+)', tr)
        if len(tds) != 8 or not st:
            continue
        txt = [re.sub(r'<[^>]+>', '', t).strip() for t in tds]
        rows.append({'name': txt[0], 'river': txt[1], 'station': st.group(1), 'fsc': txt[4],
                     'this': txt[5], 'last': txt[6], 'year': txt[7]})
    return (m.group(1).strip() if m else None, m.group(2) if m else None, rows)
out = {}
for f in sorted(glob.glob(sys.argv[1] + '/*.html')):
    prov, date, rows = parse(f)
    out[os.path.basename(f)[:-5]] = {'province': prov, 'date': date, 'dams': rows}
    print(os.path.basename(f), prov, date, len(rows))
json.dump(out, open(sys.argv[2], 'w'), indent=1)
