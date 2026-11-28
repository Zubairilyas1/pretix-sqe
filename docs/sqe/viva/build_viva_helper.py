"""
Build VIVA_MASTER_DEMO_HELPER.pdf from VIVA_MASTER_DEMO_HELPER.md (cover, contents with page numbers, content).

    python docs/sqe/viva/build_viva_helper.py
"""
import datetime
import html
import re
from pathlib import Path

import markdown
from playwright.sync_api import sync_playwright
from pypdf import PdfReader

HERE = Path(__file__).resolve().parent
SRC = HERE / "VIVA_MASTER_DEMO_HELPER.md"
OUT = HERE / "VIVA_MASTER_DEMO_HELPER.pdf"
CSS = """
@page { size: A4; margin: 16mm 15mm; }
body { font-family: 'Segoe UI', Arial, sans-serif; font-size: 10pt; line-height: 1.42; color: #111; }
.cover { padding-top: 70mm; text-align: center; page-break-after: always; }
.cover h1 { font-size: 26pt; margin: 0 0 4mm; border: none; page-break-before: avoid; color: #1f3b73; }
.cover .sub { font-size: 13pt; color: #333; margin: 2mm 0; }
.cover table { margin: 10mm auto 0; width: 70%; border-collapse: collapse; font-size: 11pt; }
.cover td, .cover th { border: none; border-bottom: 0.6px solid #bbb; padding: 4px 8px; text-align: left; min-width: 0;
                       white-space: nowrap; }
h1 { font-size: 18pt; border-bottom: 2px solid #1f3b73; color: #1f3b73; padding-bottom: 3px; page-break-before: always;
     margin-top: 0; }
h1.toc-title { page-break-before: avoid; }
h2 { font-size: 13pt; color: #1f3b73; margin-top: 14px; border-bottom: 0.6px solid #ccd; }
h3 { font-size: 11pt; margin-top: 10px; }
table { border-collapse: collapse; width: 100%; margin: 5px 0 9px; font-size: 8.8pt; }
th, td { border: 0.6px solid #888; padding: 3px 5px; vertical-align: top; overflow-wrap: anywhere; min-width: 3.5em; }
th { background: #e6ebf5; } tr { page-break-inside: avoid; }
code { font-family: Consolas, monospace; font-size: 8.6pt; background: #f1f3f7; padding: 0 2px; }
pre { background: #0f1724; color: #e6edf3; padding: 7px 9px; font-size: 8.3pt; white-space: pre-wrap;
      border-radius: 3px; page-break-inside: avoid; }
pre code { background: none; color: inherit; }
ol li, ul li { margin: 2px 0; }
.toc { width: 100%; border-collapse: collapse; }
.toc td { border: none; padding: 2px 2px; min-width: 0; font-size: 10pt; }
.toc td.p { text-align: right; width: 12mm; }
.toc tr.l1 td { font-weight: bold; padding-top: 7px; }
.toc tr.l2 td.t { padding-left: 7mm; }
"""


def body_html():
    text = SRC.read_text(encoding="utf-8")
    return markdown.markdown(text, extensions=["tables", "fenced_code", "sane_lists"])


def headings(body):
    return [(int(m.group(1)), re.sub(r"<[^>]+>", "", m.group(2)))
            for m in re.finditer(r"<h([12])>(.*?)</h\1>", body)]


def build(pages=None):
    pages = pages or {}
    body = body_html()
    heads = headings(body)
    rows = "".join(f'<tr class="l{lvl}"><td class="t">{html.escape(t)}</td><td class="p">{pages.get(i, "000")}</td></tr>'
                   for i, (lvl, t) in enumerate(heads))
    cover = f"""<div class="cover"><div class="sub">SE3002 Software Quality Engineering &middot; Fall 2026 &middot; Section B</div>
<h1>Viva and Live Demo Guide</h1><div class="sub">pretix-sqe final project: demo scripts, live tasks, question bank</div>
<table><tr><th>Member</th><th>Roll number</th><th>Area</th></tr>
<tr><td>Zubair</td><td>24I-3142</td><td>Area 1: white-box, mutation, CI</td></tr>
<tr><td>Sami</td><td>24I-3070</td><td>Area 2: API testing, test data</td></tr>
<tr><td>Tawassul</td><td>24I-3100</td><td>Area 3: use cases, usability, security, performance</td></tr></table>
<div class="sub" style="margin-top:12mm;font-size:10pt">Built {datetime.date.today().isoformat()} from
docs/sqe/viva/VIVA_MASTER_DEMO_HELPER.md</div></div>"""
    toc = f'<h1 class="toc-title">Contents</h1><table class="toc">{rows}</table>'
    return f"<!doctype html><html><head><meta charset='utf-8'><style>{CSS}</style></head><body>{cover}{toc}{body}</body></html>", heads


def render(doc):
    tmp = HERE / "_viva.html"
    tmp.write_text(doc, encoding="utf-8")
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page()
        pg.goto(tmp.as_uri(), wait_until="load")
        pg.pdf(path=str(OUT), format="A4", print_background=True, display_header_footer=True,
               header_template="<div></div>",
               footer_template="<div style='font-size:8px;width:100%;text-align:center;color:#555'>Viva and live demo"
                               " guide &middot; page <span class='pageNumber'></span> of <span class='totalPages'></span></div>",
               margin={"top": "14mm", "bottom": "15mm", "left": "14mm", "right": "14mm"})
        b.close()
    tmp.unlink()


def find(heads):
    texts = [re.sub(r"\s+", " ", (p.extract_text() or "")).lower() for p in PdfReader(str(OUT)).pages]
    start = next(i for i, t in enumerate(texts) if i > 1 and t.startswith(heads[0][1].lower()[:30]))
    out, cur = {}, start
    for i, (_, t) in enumerate(heads):
        key = re.sub(r"\s+", " ", t).lower()[:45]
        for j in range(cur, len(texts)):
            if key in texts[j]:
                out[i], cur = j + 1, j
                break
    return out


if __name__ == "__main__":
    doc, heads = build()
    render(doc)
    doc, heads = build(find(heads))
    render(doc)
    print("written", OUT, len(PdfReader(str(OUT)).pages), "pages")
