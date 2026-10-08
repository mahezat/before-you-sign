"""Run one of the agent's ES|QL tools directly against Elasticsearch, without the LLM.

Usage:
  python scripts/query.py elastic/esql/bys_grade_building.esql bbl=2028190051
  python scripts/query.py elastic/esql/bys_find_building.esql "address=1515 SELWYN AVENUE"
  python scripts/query.py elastic/esql/bys_better_nearby.esql bbl=2026100012
"""
import sys

import requests

from common import ES, es_headers


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    query = open(sys.argv[1]).read()
    params = []
    for arg in sys.argv[2:]:
        k, v = arg.split("=", 1)
        params.append({k: int(v) if v.isdigit() and k != "bbl" else v})
    body = {"query": query}
    if params:
        body["params"] = params
    r = requests.post(f"{ES}/_query?format=txt", headers=es_headers(), json=body, timeout=120)
    print(r.text if r.ok else f"{r.status_code} {r.text}")


if __name__ == "__main__":
    main()
