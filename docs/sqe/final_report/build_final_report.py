"""
Build the final project PDF from the Markdown documents that live in the repository.

    python docs/sqe/final_report/build_final_report.py [--rolls 24I-0000,24I-0001,24I-0002] [--section A]

The report is the concatenation of the documents listed in SECTIONS (unchanged content, headings demoted by one
level), rendered with Python-Markdown and printed to PDF with Playwright/Chromium. Relative image links are resolved
against the source file, so figures appear in the PDF. Output:
    docs/sqe/final_report/Project_<rolls>_<section>.pdf   (or FINAL_REPORT.pdf when no rolls are given)
"""
import argparse
import datetime
import json
import re
import subprocess
from pathlib import Path

import markdown
from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
T = "src/tests/team"
SECTIONS = [
    ("Overview", ["docs/sqe/final_report/00_front.md"]),
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
EXTRA_FIGURES = {  # figures that documents mention by path but do not embed
    "13. Defect management and root cause analysis": [("docs/sqe/figures/pareto_defects.png", "Defects by category (Pareto)")],
}
CSS = """
@page { size: A4; margin: 18mm 15mm 18mm 15mm; }
body { font-family: 'Times New Roman', serif; font-size: 10.5pt; line-height: 1.35; color: #000; }
h1.part { page-break-before: always; font-size: 17pt; border-bottom: 1.5px solid #000; padding-bottom: 4px; }
h1.part.first { page-break-before: avoid; }
h2 { font-size: 13.5pt; margin-top: 14px; } h3 { font-size: 12pt; } h4, h5 { font-size: 11pt; }
table { border-collapse: collapse; width: 100%; margin: 6px 0 10px; font-size: 8.6pt; page-break-inside: auto; }
th, td { border: 0.6px solid #555; padding: 3px 4px; vertical-align: top; word-break: normal; overflow-wrap: anywhere; hyphens: none; min-width: 4.6em; }
th { background: #e8e8e8; } tr { page-break-inside: avoid; }
code { font-family: Consolas, monospace; font-size: 8.6pt; background: #f2f2f2; padding: 0 2px; }
pre { background: #f5f5f5; border: 0.5px solid #bbb; padding: 6px; font-size: 8pt; white-space: pre-wrap; }
pre code { background: none; }
img { max-width: 100%; max-height: 190mm; display: block; margin: 6px auto; }
.src { font-size: 8pt; color: #444; margin: -4px 0 8px; }
.caption { text-align: center; font-size: 9pt; font-style: italic; }
"""


def _git(*a):
    return subprocess.run(["git", *a], cwd=REPO, capture_output=True, text=True).stdout.strip()


def _render(path, replacements):
    text = (REPO / path).read_text(encoding="utf-8")
    for k, v in replacements.items():
        text = text.replace(k, v)
    text = re.sub(r"^(#{1,5}) ", lambda m: "#" + m.group(1) + " ", text, flags=re.M)  # demote headings

    def img(m):
        target = (REPO / path).parent / m.group(2)
        return f"![{m.group(1)}]({target.resolve().as_uri()})" if target.exists() else m.group(0)
    text = re.sub(r"!\[([^\]]*)\]\((?!https?:)([^)]+)\)", img, text)
    html = markdown.markdown(text, extensions=["tables", "fenced_code", "sane_lists"])
    return f'<p class="src">Source: <code>{path}</code></p>' + html


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rolls", help="comma separated roll numbers, e.g. 24I-3142,24I-3070,24I-3100")
    ap.add_argument("--section", default="SECTION")
    a = ap.parse_args()
    rolls = a.rolls.split(",") if a.rolls else ["ROLL_ZUBAIR", "ROLL_SAMI", "ROLL_TAWASSUL"]
    summary = REPO / T / "zubair/mutation/results/run2_after_kills/summary.json"
    score = "see section 7"
    if summary.exists():
        s = json.loads(summary.read_text())
        score = f"{s['mutation_score_percent']} % ({s['killed']}/{s['killed'] + s['survived']})"
    repl = {"ROLL_ZUBAIR": rolls[0], "ROLL_SAMI": rolls[1], "ROLL_TAWASSUL": rolls[2], "SECTION": a.section,
            "BUILD_COMMIT": _git("rev-parse", "--short", "HEAD"), "BUILD_DATE": datetime.date.today().isoformat(),
            "RUN2_SCORE": score}
    parts, missing = [], []
    for i, (title, files) in enumerate(SECTIONS):
        cls = "part first" if i == 0 else "part"
        body = []
        for f in files:
            if (REPO / f).exists():
                body.append(_render(f, repl if f.endswith("00_front.md") else {}))
            else:
                missing.append(f)
        for fig, cap in EXTRA_FIGURES.get(title, []):
            body.append(f'<img src="{(REPO / fig).resolve().as_uri()}"><p class="caption">{cap} ({fig})</p>')
        heading = "" if i == 0 else f'<h1 class="{cls}">{title}</h1>'
        parts.append(heading + "\n".join(body))
    html = f"<!doctype html><html><head><meta charset='utf-8'><style>{CSS}</style></head><body>{''.join(parts)}</body></html>"
    html_path = HERE / "final_report.html"
    html_path.write_text(html, encoding="utf-8")
    name = f"Project_{'_'.join(rolls)}_{a.section}.pdf" if a.rolls else "FINAL_REPORT.pdf"
    out = HERE / name
    with sync_playwright() as p:
        b = p.chromium.launch()
        page = b.new_page()
        page.goto(html_path.as_uri(), wait_until="networkidle")
        page.pdf(path=str(out), format="A4", print_background=True, display_header_footer=True,
                 header_template="<div></div>",
                 footer_template="<div style='font-size:8px;width:100%;text-align:center'>"
                                 "pretix-sqe final report - page <span class='pageNumber'></span> / "
                                 "<span class='totalPages'></span></div>",
                 margin={"top": "16mm", "bottom": "16mm", "left": "14mm", "right": "14mm"})
        b.close()
    if missing:
        print("MISSING SOURCES:", *missing, sep="\n  ")
    print("written", out)


if __name__ == "__main__":
    main()
