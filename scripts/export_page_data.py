"""Export every graded building from Elasticsearch for the static report-card page.

Writes web/data/grades.json and web/data/cats.json. Grades use the same per-apartment
rubric as the bys_grade_building agent tool, so the page and the agent always agree.

ES|QL returns at most 10,000 rows per query, so buildings are pulled in chunks by BBL prefix.

Usage: python scripts/export_page_data.py
"""
import json
import os
from collections import Counter

import requests

from common import ES, es_headers, ROOT

GRADES = """FROM hpd_violations, evictions METADATA _index
| WHERE bbl LIKE ?prefix
| EVAL is_v = CASE(_index == "hpd_violations", 1, 0), is_e = CASE(_index == "evictions", 1, 0),
       r = CASE(rentimpairing == "Y", 1, 0), lat = ST_Y(location), lon = ST_X(location),
       addr_h = CASE(_index == "hpd_violations", address.keyword, null)
| STATS v = SUM(is_v), e = SUM(is_e), rimp = SUM(r), oldest = MIN(inspectiondate), last_e = MAX(executed_date),
        addr_h = MAX(addr_h), addr_any = MAX(address.keyword), lat = MAX(lat), lon = MAX(lon), apts = MAX(units) BY bbl
| EVAL yrs = DATE_DIFF("day", TO_DATETIME("2017-01-01T00:00:00.000Z"), NOW()) / 365.25
| EVAL days = DATE_DIFF("day", oldest, NOW()), addr = COALESCE(addr_h, addr_any),
       vpa = ROUND(TO_DOUBLE(v) / apts, 2), epy = ROUND(TO_DOUBLE(e) * 100.0 / apts / yrs, 2)
| EVAL grade = CASE(v == 0 AND e == 0, "A", apts IS NULL, "N",
                    vpa >= 1.0 OR epy >= 3.0, "F",
                    vpa >= 0.5 OR epy >= 2.0, "D",
                    vpa >= 0.2 OR epy >= 1.0 OR days > 730, "C", "B")
| KEEP bbl, addr, grade, v, e, rimp, oldest, last_e, lat, lon, apts, vpa, epy
| LIMIT 10000"""

# Violation categories per building, for the "What's wrong here" bars and the household lens.
# P pests, L lead paint, M mold, H heat or hot water, F fire safety, W window guards, K leaks, O other.
CATS = """FROM hpd_violations
| WHERE bbl LIKE ?prefix
| EVAL d = TO_UPPER(novdescription)
| EVAL c = CASE(d LIKE "*LEAD*", "L", d LIKE "*MOLD*", "M",
                d LIKE "*MICE*" OR d LIKE "*RODENT*" OR d LIKE "*RATS*" OR d LIKE "*ROACH*" OR d LIKE "*VERMIN*" OR d LIKE "*BEDBUG*" OR d LIKE "*PEST*", "P",
                d LIKE "*HEAT*" OR d LIKE "*HOT WATER*", "H",
                d LIKE "*SMOKE DETECT*" OR d LIKE "*CARBON MONOXIDE*" OR d LIKE "*FIRE*", "F",
                d LIKE "*WINDOW GUARD*", "W", d LIKE "*LEAK*" OR d LIKE "*WATER*", "K", "O")
| STATS n = COUNT(*) BY bbl, c
| LIMIT 10000"""


def run(query, prefix):
    r = requests.post(f"{ES}/_query", headers=es_headers(), json={"query": query, "params": [{"prefix": prefix}]}, timeout=120)
    r.raise_for_status()
    j = r.json()
    if len(j["values"]) >= 10000:
        raise SystemExit(f"chunk {prefix} hit the 10,000 row limit; use a longer prefix")
    return [c["name"] for c in j["columns"]], j["values"]


def main():
    out_dir = os.path.join(ROOT, "web", "data")
    os.makedirs(out_dir, exist_ok=True)

    rows = []
    for p in range(200, 206):          # Bronx BBLs start with 2; next digits are the tax block
        for d in range(10):
            cols, vals = run(GRADES, f"{p}{d}*")
            rows += [dict(zip(cols, v)) for v in vals]

    grades = []
    for r in rows:
        if r["lat"] is None or r["lon"] is None or not r["addr"]:
            continue
        grades.append([
            r["addr"], r["grade"], int(r["v"] or 0), int(r["e"] or 0), int(r["rimp"] or 0),
            (r["oldest"] or "")[:10], (r["last_e"] or "")[:10], round(r["lat"], 5), round(r["lon"], 5),
            r["bbl"], r["apts"], r["vpa"], r["epy"],
        ])
    json.dump(grades, open(os.path.join(out_dir, "grades.json"), "w"), separators=(",", ":"))
    print("buildings", len(grades), dict(Counter(g[1] for g in grades)))

    cats = {}
    for p in range(200, 206):
        for d in range(10):
            for d2 in range(10):
                _, vals = run(CATS, f"{p}{d}{d2}*")
                for n, bbl, c in vals:
                    cats.setdefault(bbl, {})[c] = n
    json.dump(cats, open(os.path.join(out_dir, "cats.json"), "w"), separators=(",", ":"))
    print("category rows for", len(cats), "buildings")


if __name__ == "__main__":
    main()
