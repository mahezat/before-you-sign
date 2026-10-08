"""Download the three NYC Open Data sets used by Before You Sign (Bronx only).

  hpd_violations.csv  HPD housing maintenance code violations (wvxf-dwi5): open, Class C (immediately hazardous)
  evictions.csv       Marshal evictions (6z8x-wfk4): residential, executed since 2017
  pluto_bx.csv        MapPLUTO tax lots (64uk-42ks): residential unit counts, used to grade per apartment

On Oct 7, 2026 these filters returned 167,819 violations, 40,754 evictions and 89,362 tax lots.
No API key is needed. Usage: python scripts/download_data.py
"""
import csv
import io
import os

import requests

from common import ROOT

BASE = "https://data.cityofnewyork.us/resource/"
PAGE = 50000

SETS = {
    "hpd_violations.csv": (
        "wvxf-dwi5",
        "bbl,housenumber,streetname,zip,apartment,class,novdescription,inspectiondate,violationstatus,rentimpairing,nta,latitude,longitude",
        "boroid='2' AND class='C' AND violationstatus='Open'",
    ),
    "evictions.csv": (
        "6z8x-wfk4",
        "bbl,eviction_address,eviction_zip,executed_date,nta,latitude,longitude",
        "borough='BRONX' AND residential_commercial_ind='Residential'",
    ),
    "pluto_bx.csv": (
        "64uk-42ks",
        "bbl,unitsres",
        "borough='BX'",
    ),
}


def fetch(dataset, select, where, path):
    fields = select.split(",")
    n = 0
    with open(path, "w", newline="") as f:
        w = csv.writer(f, quoting=csv.QUOTE_ALL)
        w.writerow(fields)
        offset = 0
        while True:
            params = {"$select": select, "$where": where, "$order": ":id", "$limit": PAGE, "$offset": offset}
            r = requests.get(BASE + dataset + ".csv", params=params, timeout=300)
            r.raise_for_status()
            rows = list(csv.reader(io.StringIO(r.text)))[1:]
            if not rows:
                break
            w.writerows(rows)
            n += len(rows)
            offset += PAGE
    return n


def main():
    out = os.path.join(ROOT, "data")
    os.makedirs(out, exist_ok=True)
    for name, (dataset, select, where) in SETS.items():
        n = fetch(dataset, select, where, os.path.join(out, name))
        print(f"{name}: {n:,} rows")


if __name__ == "__main__":
    main()
