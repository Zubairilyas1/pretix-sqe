"""
Real SonarQube screenshots for the report.

Starts a local SonarQube Community Build (same image as CI Gate 4), sets it up exactly like CI
(src/tests/team/zubair/ci/sonar_setup.py: project, quality gate, token), analyses
  1. pretix-sqe-quotas : quotas.py with the Area 1 coverage report (the CI project)
  2. pretix-sqe-w1w2   : the four W1/W2 files analysed in Area 3 (sonar_findings.md)
with pysonar (official SonarScanner for Python), logs in to the web UI with Playwright and saves screenshots to
docs/sqe/final_report/figures/sonar_*.png.

    python docs/sqe/final_report/capture/capture_sonar.py        (from the repository root, Docker running)
"""
import json
import os
import re
import subprocess
import sys
import time
import urllib.parse
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
FIG = REPO / "docs/sqe/final_report/figures"
PY = REPO / ".venv/Scripts/python.exe"
PYSONAR = REPO / ".venv/Scripts/pysonar.exe"
sys.path.insert(0, str(REPO / "src/tests/team/zubair/ci"))
import sonar_setup as ss  # noqa: E402

IMAGE = "sonarqube:25.1.0.102122-community"
W1W2 = ["src/pretix/base/services/cart.py", "src/pretix/base/services/orders.py",
        "src/pretix/base/models/items.py", "src/pretix/control/views/item.py"]


def scan(token, key, name, sources, extra=()):
    subprocess.run([str(PYSONAR), f"--sonar-host-url={ss.HOST}", f"--sonar-token={token}",
                    f"--sonar-project-key={key}", f"-Dsonar.projectName={name}",
                    "-Dsonar.sources=" + ",".join(sources), "-Dsonar.python.version=3.11",
                    "-Dsonar.scm.disabled=true", "-Dsonar.sourceEncoding=UTF-8",
                    "-Dsonar.qualitygate.wait=true", *extra], check=True, cwd=REPO)


def main():
    subprocess.run(["docker", "rm", "-f", "sqe-sonar-shots"], capture_output=True)
    subprocess.run(["docker", "run", "-d", "--name", "sqe-sonar-shots", "-p", "9000:9000", IMAGE], check=True)
    try:
        ss.setup("99")                                   # same project + gate + conditions as CI Gate 4
        token = ss.call("/api/user_tokens/generate", "POST", {"name": f"shots-{int(time.time())}",
                                                               "type": "GLOBAL_ANALYSIS_TOKEN"})["token"]
        # Area 1 coverage report, the same command as CI Gate 4
        subprocess.run([str(PY), "-m", "pytest", "tests/team/zubair", "-q", "-p", "no:cacheprovider",
                        "--ignore=tests/team/zubair/test_custom_mutation_operators.py",
                        "--cov=pretix.base.services.quotas", "--cov-branch",
                        "--cov-report=xml:../coverage-sonar.xml"], check=True, cwd=REPO / "src")
        xml = (REPO / "coverage-sonar.xml").read_text("utf-8")
        xml = re.sub(r"<source>.*?</source>", "<source>src</source>", xml)
        (REPO / "coverage-sonar.xml").write_text(xml, "utf-8")
        scan(token, ss.PROJECT, "pretix SQE - QuotaAvailability (critical module)",
             ["src/pretix/base/services/quotas.py"],
             ["-Dsonar.python.coverage.reportPaths=coverage-sonar.xml"])
        ss.call("/api/projects/create", "POST", {"project": "pretix-sqe-w1w2", "name": "pretix W1/W2 files (Area 3)"})
        scan(token, "pretix-sqe-w1w2", "pretix W1/W2 files (Area 3)", W1W2)
        shots()
    finally:
        subprocess.run(["docker", "rm", "-f", "sqe-sonar-shots"], capture_output=True)
        (REPO / "coverage-sonar.xml").unlink(missing_ok=True)


def shots():
    from playwright.sync_api import sync_playwright
    FIG.mkdir(parents=True, exist_ok=True)
    gate = ss.call("/api/qualitygates/list")
    gate_name = next(g["name"] for g in gate["qualitygates"] if g["name"] == ss.GATE)
    q = urllib.parse.quote
    quotas_file = f"{ss.PROJECT}:src/pretix/base/services/quotas.py"
    pages = [
        ("sonar_01_quotas_overview", f"/dashboard?id={ss.PROJECT}&codeScope=overall", None),
        ("sonar_02_quality_gate", f"/quality_gates/show/{q(gate_name)}", True),
        ("sonar_03_quotas_measures", f"/component_measures?id={ss.PROJECT}&metric=coverage&view=list", None),
        ("sonar_04_quotas_code_coverage",
         f"/code?id={ss.PROJECT}&selected={q(quotas_file)}&line=355", None),
        ("sonar_05_quotas_issues", f"/project/issues?id={ss.PROJECT}&resolved=false", None),
        ("sonar_06_w1w2_overview", "/dashboard?id=pretix-sqe-w1w2&codeScope=overall", None),
        ("sonar_07_w1w2_complexity", "/component_measures?id=pretix-sqe-w1w2&metric=complexity&view=list", None),
        ("sonar_08_w1w2_issues", "/project/issues?id=pretix-sqe-w1w2&resolved=false", None),
    ]
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1440, "height": 900})
        pg.goto(ss.HOST + "/sessions/new")
        pg.fill("input#login-input", "admin")
        pg.fill("input#password-input", ss.NEW_PW)
        pg.keyboard.press("Enter")
        pg.wait_for_url(re.compile(r"/projects"), timeout=60_000)
        # one-time onboarding pop-ups (promotion, product tour) are dismissed once; SonarQube remembers it per user
        pg.goto(ss.HOST + f"/dashboard?id={ss.PROJECT}")
        pg.wait_for_load_state("networkidle")
        time.sleep(3)
        for txt in ("Dismiss", "Got it", "Skip", "Later"):
            loc = pg.get_by_role("button", name=txt, exact=True)
            for i in range(loc.count()):
                try:
                    loc.nth(i).click(timeout=1500)
                    time.sleep(0.5)
                except Exception:
                    pass
        for sel in ("[aria-label='Dismiss']", "button[aria-label='Close']"):   # info banners at the top
            for el in pg.locator(sel).all():
                try:
                    el.click(timeout=1000)
                except Exception:
                    pass
        for name, path, full in pages:
            pg.goto(ss.HOST + path)
            pg.wait_for_load_state("networkidle")
            time.sleep(2.5)
            pg.keyboard.press("Escape")
            for el in pg.get_by_text("Dismiss", exact=True).all():   # promotion box in the corner
                try:
                    el.click(timeout=1500)
                except Exception:
                    pass
            time.sleep(0.8)
            pg.screenshot(path=str(FIG / f"{name}.png"), full_page=bool(full))
            print("saved", name)
            if name == "sonar_02_quality_gate":       # the overall-code conditions are further down the panel
                pg.get_by_text("Conditions on Overall Code").first.scroll_into_view_if_needed()
                time.sleep(0.8)
                pg.screenshot(path=str(FIG / "sonar_02b_quality_gate_overall_conditions.png"))
                print("saved sonar_02b_quality_gate_overall_conditions")
        b.close()
    meas = ss.call(f"/api/measures/component?component={ss.PROJECT}&metricKeys=coverage,line_coverage,"
                   "branch_coverage,bugs,vulnerabilities,code_smells,sqale_rating,reliability_rating,security_rating,"
                   "duplicated_lines_density,alert_status")
    (FIG / "sonar_measures.json").write_text(json.dumps(
        {"date": time.strftime("%Y-%m-%d %H:%M"), "image": IMAGE,
         "quotas": {m["metric"]: m.get("value") for m in meas["component"]["measures"]}}, indent=2), "utf-8")


if __name__ == "__main__":
    os.chdir(REPO)
    main()
