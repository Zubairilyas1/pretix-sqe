"""
Build the final project PDF from the Markdown documents that live in the repository.

    python docs/sqe/final_report/build_final_report.py --rolls 24I-3142,24I-3070,24I-3100 --section B

Layout: cover page, table of contents and list of figures (with page numbers), then one chapter per deliverable.
Each chapter is the corresponding repository document (content unchanged, headings demoted by one level), followed by
its evidence figures from figures_manifest.py. Screenshots are embedded exactly as captured (no cropping or editing).
Page numbers are found in a first rendering pass (pypdf text search) and written into the contents in a second pass.
Output: docs/sqe/final_report/Project_<rolls>_<section>.pdf
"""
import argparse
import datetime
import html
import json
import re
import subprocess
from pathlib import Path

import markdown
from playwright.sync_api import sync_playwright
from pypdf import PdfReader

from figures_manifest import FIGURES

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
FIG = HERE / "figures"
T = "src/tests/team"
SECTIONS = [
    ("Overview and release decision", ["docs/sqe/final_report/00_front.md"]),
    ("1. System, scope and test plan", [f"{T}/shared_management/TEST_PLAN.md"]),
    ("2. Static analysis and cyclomatic complexity", [f"{T}/tawassul/static_analysis/sonar_findings.md",
                                                      f"{T}/tawassul/static_analysis/cfg_cyclomatic.md"]),
    ("3. Estimation", [f"{T}/shared_management/PROJECT_ESTIMATION_PERT.md"]),
    ("4. Risk register and exit criteria", [f"{T}/shared_management/RISK_REGISTER_5x5.md"]),
    ("5. Traceability", [f"{T}/shared_management/REQUIREMENTS_TRACEABILITY_MATRIX_RTM.md"]),
    ("6. White-box unit testing", ["docs/sqe/zubair/COVERAGE_REPORT.md", "docs/sqe/zubair/MCC_MCDC_TABLES.md"]),
    ("7. Mutation analysis and CI quality gate", ["docs/sqe/zubair/MUTATION_REPORT.md",
                                                  "docs/sqe/zubair/CI_QUALITY_GATE_REPORT.md"]),
    ("8. API testing and test-data generation", [f"{T}/sami/README.md", f"{T}/sami/generator/README.md",
                                                 f"{T}/sami/generator/regeneration_demo/REGENERATION_REPORT.md",
                                                 f"{T}/sami/api/endpoint_weaknesses.md"]),
    ("9. Use cases and use-case test automation", [f"{T}/tawassul/usecases/use_case_spec.md"]),
    ("10. Usability and accessibility", [f"{T}/tawassul/usability_a11y/a11y_findings.md",
                                         f"{T}/tawassul/usability_a11y/screen_remediation/README.md"]),
    ("11. Defensive security", [f"{T}/tawassul/security/rbac_access_matrix.md",
                                f"{T}/tawassul/security/zap_passive_scan_report.md",
                                f"{T}/tawassul/security/dependency_audit_pip.md"]),
    ("12. Performance and recovery", [f"{T}/tawassul/performance/k6_metrics_report.md"]),
    ("13. Defect management and root cause analysis", [f"{T}/shared_management/CONSOLIDATED_DEFECT_LOG.md"]),
    ("14. Monitoring", [f"{T}/shared_management/PROGRESS_REPORTS.md"]),
    ("15. Test completion report", [f"{T}/shared_management/TEST_COMPLETION_REPORT.md"]),
    ("16. AI-use record", [f"{T}/shared_management/AI_USE_DISCLOSURE_LOG.md"]),
]
MEMBERS = [("Zubair", "Area 1: white-box, mutation, CI quality gate"),
           ("Sami", "Area 2: API testing, test-data generation"),
           ("Tawassul", "Area 3: use cases, usability, security, performance")]

CSS = """
@page { size: A4; margin: 18mm 16mm 18mm 16mm; }
body { font-family: 'Times New Roman', Georgia, serif; font-size: 10.5pt; line-height: 1.38; color: #111; }
.cover { height: 255mm; display: flex; flex-direction: column; justify-content: space-between; text-align: center;
         page-break-after: always; }
.cover .top { margin-top: 18mm; font-size: 12pt; letter-spacing: .5px; color: #333; }
.cover h1 { font-size: 25pt; margin: 0 0 6mm; line-height: 1.2; border: none; }
.cover .sub { font-size: 14pt; color: #333; margin-bottom: 4mm; }
.cover .rule { width: 60%; margin: 8mm auto; border-top: 1.5px solid #222; }
.cover table { width: 72%; margin: 0 auto; font-size: 11.5pt; border-collapse: collapse; }
.cover td, .cover th { border: none; border-bottom: 0.6px solid #bbb; padding: 5px 8px; text-align: left; min-width: 0; }
.cover th { background: none; font-weight: bold; }
.cover .meta { font-size: 10pt; color: #333; line-height: 1.6; }
.front h1 { font-size: 17pt; border-bottom: 1.5px solid #222; padding-bottom: 4px; page-break-before: always; }
.toc { width: 100%; border-collapse: collapse; font-size: 10.5pt; }
.toc td { border: none; padding: 2.2px 2px; min-width: 0; vertical-align: bottom; }
.toc td.p { text-align: right; width: 12mm; }
.toc tr.l1 td { font-weight: bold; padding-top: 6px; }
.toc tr.l2 td.t { padding-left: 7mm; }
.toc tr.fig td { font-size: 9.2pt; }
.toc td.t span.dots { }
h1.part { page-break-before: always; font-size: 18pt; border-bottom: 1.5px solid #222; padding-bottom: 4px; margin-top: 0; }
h2 { font-size: 13.5pt; margin-top: 16px; } h3 { font-size: 12pt; } h4, h5 { font-size: 11pt; }
table { border-collapse: collapse; width: 100%; margin: 6px 0 10px; font-size: 8.6pt; page-break-inside: auto; }
th, td { border: 0.6px solid #666; padding: 3px 4px; vertical-align: top; word-break: normal; overflow-wrap: anywhere;
         hyphens: none; min-width: 4.6em; }
th { background: #e9e9e9; } tr { page-break-inside: avoid; }
code { font-family: Consolas, monospace; font-size: 8.6pt; background: #f2f2f2; padding: 0 2px; }
pre { background: #f6f6f6; border: 0.5px solid #bbb; padding: 6px; font-size: 8pt; white-space: pre-wrap; }
pre code { background: none; }
h2.evidence { page-break-before: always; font-size: 14pt; border-bottom: 1px solid #888; }
figure { margin: 4mm 0 6mm; page-break-inside: avoid; text-align: center; }
figure img { max-width: 100%; max-height: 205mm; border: 0.6px solid #999; }
figcaption { font-size: 9pt; margin-top: 2mm; text-align: center; }
figcaption b { font-weight: bold; }
.appendix td { font-size: 8.6pt; }
"""


def _git(*a):
    return subprocess.run(["git", *a], cwd=REPO, capture_output=True, text=True).stdout.strip()


def _slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def _render_doc(path, replacements, h2s):
    text = (REPO / path).read_text(encoding="utf-8")
    for k, v in replacements.items():
        text = text.replace(k, v)
    text = re.sub(r"^(#{1,5}) ", lambda m: "#" + m.group(1) + " ", text, flags=re.M)  # demote headings

    def img(m):
        target = (REPO / path).parent / m.group(2)
        return f"![{m.group(1)}]({target.resolve().as_uri()})" if target.exists() else m.group(0)
    text = re.sub(r"!\[([^\]]*)\]\((?!https?:)([^)]+)\)", img, text)
    body = markdown.markdown(text, extensions=["tables", "fenced_code", "sane_lists"])

    def anchor(m):  # document titles (now h2) go into the table of contents
        title = re.sub(r"<[^>]+>", "", m.group(1))
        h2s.append(title)
        return f'<h2 id="h-{_slug(title)}-{len(h2s)}">{m.group(1)}</h2>'
    return re.sub(r"<h2>(.*?)</h2>", anchor, body, count=1)


def build_html(rolls, section, pages=None):
    pages = pages or {}
    summary = REPO / T / "zubair/mutation/results/run2_after_kills/summary.json"
    score = "see section 7"
    if summary.exists():
        s = json.loads(summary.read_text())
        score = f"{s['mutation_score_percent']} % ({s['killed']}/{s['killed'] + s['survived']})"
    repl = {"ROLL_ZUBAIR": rolls[0], "ROLL_SAMI": rolls[1], "ROLL_TAWASSUL": rolls[2], "SECTION": section,
            "BUILD_COMMIT": _git("rev-parse", "--short", "HEAD"), "BUILD_DATE": datetime.date.today().isoformat(),
            "RUN2_SCORE": score}
    toc, figs, parts = [], [], []
    for ci, (title, files) in enumerate(SECTIONS):
        h2s = []
        body = [_render_doc(f, repl if f.endswith("00_front.md") else {}, h2s) for f in files if (REPO / f).exists()]
        chap = title.split(".")[0] if title[0].isdigit() else ""
        evidence = []
        for fi, (f, cap) in enumerate(FIGURES.get(title, []), 1):
            p = (FIG / f).resolve()
            if not p.exists():
                print("  missing figure:", f)
                continue
            num = f"{chap}.{len(evidence) + 1}"
            figs.append((f"Figure {num}", cap))
            evidence.append(f'<figure><img src="{p.as_uri()}"><figcaption><b>Figure {num}.</b> '
                            f'{html.escape(cap)}</figcaption></figure>')
        if evidence:
            h2s.append(f"Evidence for chapter {chap}")
            body.append(f'<h2 class="evidence">Evidence for chapter {chap}</h2>' + "\n".join(evidence))
        toc.append((1, title))
        toc.extend((2, h) for h in h2s)
        parts.append(f'<h1 class="part">{html.escape(title)}</h1>' + "\n".join(body))

    def pg(key):
        return str(pages.get(key, "000"))
    toc_rows = "".join(f'<tr class="l{lvl}"><td class="t">{html.escape(t)}</td><td class="p">{pg(("toc", i))}</td></tr>'
                       for i, (lvl, t) in enumerate(toc))
    fig_rows = "".join(f'<tr class="fig"><td class="t"><b>{n}</b> {html.escape(c)}</td><td class="p">{pg(("fig", n))}</td></tr>'
                       for n, c in figs)
    members = "".join(f"<tr><td>{n}</td><td>{r}</td><td>{a}</td></tr>" for (n, a), r in zip(MEMBERS, rolls))
    cover = f"""<div class="cover">
<div class="top">SE3002 Software Quality Engineering &middot; Fall 2026 &middot; Section {section}</div>
<div><h1>Automated Testing of an Open-Source<br>Management Information System</h1>
<div class="sub">pretix (event ticketing): ticket capacity and order workflows</div>
<div class="sub">Final Project Report</div><div class="rule"></div>
<table><tr><th>Member</th><th>Roll number</th><th>Owned area</th></tr>{members}</table></div>
<div class="meta">Section {section}<br>Public repository: https://github.com/Zubairilyas1/pretix-sqe<br>
Upstream: https://github.com/pretix/pretix &middot; baseline commit c0d887738b6cd97f724b926718c55e2ae87c9901<br>
Report built on {repl['BUILD_DATE']} from repository commit {repl['BUILD_COMMIT']}</div></div>"""
    front = (f'<div class="front"><h1 style="page-break-before:avoid">Table of contents</h1>'
             f'<table class="toc">{toc_rows}</table>'
             f'<h1>List of figures</h1><table class="toc">{fig_rows}</table></div>')
    sources = "".join(f"<tr><td>{html.escape(t)}</td><td><code>{html.escape(f)}</code></td></tr>"
                      for t, fs in SECTIONS for f in fs)
    appendix = (f'<h1 class="part">Appendix: source documents</h1><p>Every chapter is generated from the following '
                f'repository files (path relative to the repository root).</p>'
                f'<table class="appendix"><tr><th>Chapter</th><th>Source document</th></tr>{sources}</table>')
    doc = (f"<!doctype html><html><head><meta charset='utf-8'><style>{CSS}</style></head><body>"
           f"{cover}{front}{''.join(parts)}{appendix}</body></html>")
    return doc, toc, figs


def render_pdf(doc, out, label):
    html_path = HERE / "final_report.html"
    html_path.write_text(doc, encoding="utf-8")
    with sync_playwright() as p:
        b = p.chromium.launch()
        page = b.new_page()
        page.goto(html_path.as_uri(), wait_until="networkidle")
        page.pdf(path=str(out), format="A4", print_background=True, display_header_footer=True,
                 header_template="<div></div>",
                 footer_template=f"<div style='font-size:8px;width:100%;text-align:center;color:#444'>{label}"
                                 " &middot; page <span class='pageNumber'></span> of <span class='totalPages'></span></div>",
                 margin={"top": "16mm", "bottom": "16mm", "left": "15mm", "right": "15mm"})
        b.close()


def find_pages(pdf, toc, figs):
    def norm(s):
        return re.sub(r"\s+", " ", s).strip().lower()
    texts = [norm(p.extract_text() or "") for p in PdfReader(str(pdf)).pages]
    # the contents pages themselves contain every title: start searching after the last contents page
    lof = min(i for i, t in enumerate(texts) if t.startswith("list of figures") or "\nlist of figures" in t
              or " list of figures figure" in t)
    first = norm(SECTIONS[0][0])
    start = next(j for j in range(lof + 1, len(texts)) if texts[j].startswith(first))
    pages, cur = {}, start
    for i, (lvl, title) in enumerate(toc):
        key = norm(title)[:60]
        for j in range(cur, len(texts)):
            if key in texts[j]:
                pages[("toc", i)] = j + 1
                cur = j
                break
    cur = start
    for n, cap in figs:
        key = norm(f"{n}. {cap}")[:50]
        for j in range(cur, len(texts)):
            if key in texts[j]:
                pages[("fig", n)] = j + 1
                cur = j
                break
    return pages


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rolls", default="24I-3142,24I-3070,24I-3100")
    ap.add_argument("--section", default="B")
    a = ap.parse_args()
    rolls = a.rolls.split(",")
    name = f"Project_{'_'.join(rolls)}_{a.section}"
    out = HERE / f"{name}.pdf"
    doc, toc, figs = build_html(rolls, a.section)
    render_pdf(doc, out, name)                                 # pass 1: placeholders "000"
    pages = find_pages(out, toc, figs)
    doc, toc, figs = build_html(rolls, a.section, pages)
    render_pdf(doc, out, name)                                 # pass 2: real page numbers
    missing = [t for i, (_, t) in enumerate(toc) if ("toc", i) not in pages]
    if missing:
        print("contents entries without page number:", missing)
    print(f"written {out} ({len(PdfReader(str(out)).pages)} pages, {len(figs)} figures)")


if __name__ == "__main__":
    main()
