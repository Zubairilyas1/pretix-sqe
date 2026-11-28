"""
Screenshots of the real HTML reports produced by the tools (coverage.py, Cosmic Ray, pytest-html, Lighthouse,
OWASP ZAP, Swagger UI rendering of our OpenAPI spec). Every screenshot is taken in Chromium from the report file
that the tool wrote; nothing is drawn.

    python docs/sqe/final_report/capture/capture_reports.py           (from the repository root)
"""
import json
import time
from pathlib import Path

import yaml
from playwright.sync_api import sync_playwright

REPO = Path(__file__).resolve().parents[4]
FIG = REPO / "docs/sqe/final_report/figures"
HTML = REPO / "docs/sqe/final_report/evidence_html"   # pytest-html reports generated for the report
T = REPO / "src/tests/team"
LH = T / "tawassul/usability_a11y/reports"


def uri(p):
    return Path(p).resolve().as_uri()


def shot(pg, name, url=None, full=False, clip_selector=None, wait=1.0):
    if url:
        pg.goto(url)
        pg.wait_for_load_state("networkidle")
    time.sleep(wait)
    path = str(FIG / f"{name}.png")
    if clip_selector:
        pg.locator(clip_selector).first.screenshot(path=path)
    else:
        pg.screenshot(path=path, full_page=full)
    print("saved", name)


def coverage(pg):
    cov = REPO / "docs/sqe/zubair/evidence/htmlcov_quotas"
    shot(pg, "cov_01_index", uri(cov / "index.html"))
    shot(pg, "cov_02_function_index", uri(cov / "function_index.html"))
    f = next(cov.glob("z_*_quotas_py.html"))
    pg.goto(uri(f) + "#t355")
    pg.wait_for_load_state("networkidle")
    shot(pg, "cov_03_quotas_branches")


def cosmic_ray(pg):
    for run in ("run1_baseline", "run2_after_kills"):
        rep = T / f"zubair/mutation/results/{run}/report.html"
        pg.goto(uri(rep))
        pg.wait_for_load_state("load")
        shot(pg, f"mut_{run}_summary")
    # run 2: open the job list and show one surviving (equivalent) mutant and one custom-operator mutant
    pg.goto(uri(T / "zubair/mutation/results/run2_after_kills/report.html"))
    pg.wait_for_load_state("load")
    pg.evaluate("$('#job_list___collapse_1').collapse('show')")
    time.sleep(1)
    for name, needle in (("mut_run2_survivor", "TestOutcome.SURVIVED"),
                         ("mut_run2_custom_operator", "operator: sqe/SwapAvailabilityVerdict")):
        card_id = pg.evaluate("""(needle) => {
            for (const c of [...document.querySelectorAll('a.job_list___sub_multi_heading')].map(a => a.parentElement)) {
                if (c.textContent.includes(needle)) {
                    const col = c.querySelector('.collapse'); $(col).collapse('show'); return col.id; }
            } return null; }""", needle)
        if not card_id:
            print("not found:", needle)
            continue
        time.sleep(1.2)
        card = pg.locator(f"#{card_id}").locator("xpath=..")
        card.scroll_into_view_if_needed()
        card.screenshot(path=str(FIG / f"{name}.png"))
        print("saved", name)
        pg.evaluate("(id) => $('#' + id).collapse('hide')", card_id)
        time.sleep(0.8)


def pytest_html(pg):
    for name, f in (("pytest_area1", HTML / "area1-report.html"), ("pytest_area2", HTML / "area2-report.html"),
                    ("pytest_area3", HTML / "area3-report.html")):
        if f.exists():
            shot(pg, name, uri(f), wait=1.5)


def lighthouse(pg):
    reports = sorted(LH.glob("lighthouse_*.report.html")) + sorted((LH / "usecases").glob("lighthouse_*.report.html"))
    for f in reports:
        name = "lh_" + f.name.replace("lighthouse_", "").replace(".report.html", "")
        pg.goto(uri(f))
        pg.wait_for_load_state("networkidle")
        time.sleep(2.5)                       # score gauges animate
        shot(pg, name)


def zap(pg):
    rep = T / "tawassul/security/evidence/zap_report.html"
    shot(pg, "zap_01_summary", uri(rep))
    pg.goto(uri(rep) + "#10020")
    time.sleep(1)
    shot(pg, "zap_02_alert_10020")


def swagger(pg):
    spec = yaml.safe_load((T / "sami/openapi/pretix_orders_api.yaml").read_text("utf-8"))
    page = HTML / "swagger_ui.html"
    page.write_text("""<!doctype html><html><head><meta charset="utf-8"><title>pretix orders API (OpenAPI)</title>
<link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist@5.17.14/swagger-ui.css"></head><body>
<div id="ui"></div><script src="https://unpkg.com/swagger-ui-dist@5.17.14/swagger-ui-bundle.js"></script>
<script>window.ui = SwaggerUIBundle({spec: %s, dom_id: '#ui', docExpansion: 'list', defaultModelsExpandDepth: -1});
</script></body></html>""" % json.dumps(spec), "utf-8")
    shot(pg, "api_01_swagger_overview", uri(page), wait=3)
    op = pg.locator(".opblock-post").filter(has_text="orders").first
    op.locator(".opblock-summary").click()
    time.sleep(1.5)
    op.screenshot(path=str(FIG / "api_02_swagger_create_order.png"))
    print("saved api_02_swagger_create_order")


def main():
    FIG.mkdir(parents=True, exist_ok=True)
    HTML.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1366, "height": 860})
        import sys
        wanted = sys.argv[1:]
        for step in (coverage, cosmic_ray, pytest_html, lighthouse, zap, swagger):
            if wanted and step.__name__ not in wanted:
                continue
            try:
                step(pg)
            except Exception as e:
                print(f"{step.__name__} failed: {e}")
        b.close()


if __name__ == "__main__":
    main()
