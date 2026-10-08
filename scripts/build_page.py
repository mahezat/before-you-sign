"""Build the static report-card page: web/page_template.html + web/data/*.json -> docs/index.html.

The page is one self-contained HTML file (data embedded, no server, no API calls), so it can be
hosted anywhere, including GitHub Pages from the docs/ folder.
Deep links: index.html#<BBL>-<en|es|ar>, e.g. #2028190051-es

Usage: python scripts/build_page.py   (run export_page_data.py first to refresh the data)
"""
import os

from common import ROOT


def main():
    web = os.path.join(ROOT, "web")
    template = open(os.path.join(web, "page_template.html"), encoding="utf-8").read()
    grades = open(os.path.join(web, "data", "grades.json"), encoding="utf-8").read()
    cats = open(os.path.join(web, "data", "cats.json"), encoding="utf-8").read()
    body = template.replace("__GRADES__", grades).replace("__CATS__", cats)
    page = ("<!doctype html>\n<html lang=\"en\">\n<head>\n<meta charset=\"utf-8\">\n"
            "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1, viewport-fit=cover\">\n"
            "</head>\n<body>\n" + body + "\n</body>\n</html>\n")
    out = os.path.join(ROOT, "docs", "index.html")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    open(out, "w", encoding="utf-8").write(page)
    print(out, f"{len(page):,} bytes")


if __name__ == "__main__":
    main()
