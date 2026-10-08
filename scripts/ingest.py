"""Load the downloaded CSVs into two Elasticsearch indices: hpd_violations and evictions.

Each document gets:
  address   house number + street (violations) or the eviction address, as text + keyword
  location  geo_point from latitude/longitude, for the geo-distance "better nearby" search
  units     residential apartment count for the building from PLUTO, for per-apartment grading

Re-running deletes and recreates both indices. Usage: python scripts/ingest.py
"""
import csv
import json
import os

import requests

from common import ES, ROOT, es_headers

MAPPINGS = {
    "hpd_violations": {
        "properties": {
            "bbl": {"type": "keyword"},
            "units": {"type": "integer"},
            "address": {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
            "housenumber": {"type": "keyword"},
            "streetname": {"type": "keyword"},
            "zip": {"type": "keyword"},
            "apartment": {"type": "keyword"},
            "class": {"type": "keyword"},
            "novdescription": {"type": "text"},
            "inspectiondate": {"type": "date"},
            "violationstatus": {"type": "keyword"},
            "rentimpairing": {"type": "keyword"},
            "nta": {"type": "keyword"},
            "location": {"type": "geo_point"},
        }
    },
    "evictions": {
        "properties": {
            "bbl": {"type": "keyword"},
            "units": {"type": "integer"},
            "address": {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
            "eviction_zip": {"type": "keyword"},
            "executed_date": {"type": "date"},
            "nta": {"type": "keyword"},
            "location": {"type": "geo_point"},
        }
    },
}


def load_units(path):
    """PLUTO BBLs look like 2026100012.00000000; keep the 10-digit BBL and its residential units."""
    units = {}
    for r in csv.DictReader(open(path)):
        try:
            bbl = str(int(float(r["bbl"])))
            u = int(float(r["unitsres"] or 0))
        except ValueError:
            continue
        if u > 0:
            units[bbl] = u
    return units


def docs(index, path, units):
    for r in csv.DictReader(open(path)):
        d = {k: v for k, v in r.items() if v not in (None, "")}
        lat, lon = d.pop("latitude", None), d.pop("longitude", None)
        if lat and lon:
            try:
                d["location"] = {"lat": float(lat), "lon": float(lon)}
            except ValueError:
                pass
        if index == "hpd_violations":
            d["address"] = f"{d.get('housenumber', '')} {d.get('streetname', '')}".strip()
        else:
            d["address"] = d.pop("eviction_address", None)
        u = units.get(d.get("bbl", ""))
        if u:
            d["units"] = u
        yield {k: v for k, v in d.items() if v is not None}


def bulk(index, lines):
    r = requests.post(f"{ES}/{index}/_bulk", headers=es_headers("application/x-ndjson"), data="\n".join(lines) + "\n", timeout=300)
    r.raise_for_status()
    return sum(1 for it in r.json().get("items", []) if "error" in it["index"])


def load(index, path, units):
    requests.delete(f"{ES}/{index}", headers=es_headers())
    r = requests.put(f"{ES}/{index}", headers=es_headers(), json={"mappings": MAPPINGS[index]})
    r.raise_for_status()
    batch, sent, errors = [], 0, 0
    for d in docs(index, path, units):
        batch += [json.dumps({"index": {}}), json.dumps(d)]
        if len(batch) >= 10000:
            errors += bulk(index, batch)
            sent += len(batch) // 2
            batch = []
    if batch:
        errors += bulk(index, batch)
        sent += len(batch) // 2
    requests.post(f"{ES}/{index}/_refresh", headers=es_headers())
    count = requests.get(f"{ES}/{index}/_count", headers=es_headers()).json().get("count")
    print(f"{index}: sent {sent:,}, errors {errors}, indexed {count:,}")


def main():
    data = os.path.join(ROOT, "data")
    units = load_units(os.path.join(data, "pluto_bx.csv"))
    print(f"apartment counts for {len(units):,} tax lots")
    load("hpd_violations", os.path.join(data, "hpd_violations.csv"), units)
    load("evictions", os.path.join(data, "evictions.csv"), units)


if __name__ == "__main__":
    main()
