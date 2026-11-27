"""
Run Google Lighthouse (accessibility + best practices) on the two key screens.

Screens:
  * customer checkout entry: the shop page of perf-org/perf-conf
  * organizer item creation: /control/event/perf-org/perf-conf/items/add (logged in)

The organizer logs in with Playwright through the real login form, using the
exact User-Agent of the headless Chromium that Lighthouse then launches
(CHROME_PATH); the session cookie is passed with --extra-headers and UA is
set explicitly to that value. pretix pins back-office sessions to the User-Agent, so any
mismatch silently redirects to the login page; every report's final URL is
therefore checked against the intended screen.

    cd src
    ../.venv/Scripts/python tests/team/tawassul/usability_a11y/lighthouse_run.py before
    (apply the fix, restart the perf server)
    ../.venv/Scripts/python tests/team/tawassul/usability_a11y/lighthouse_run.py after
"""
import json
import os
import subprocess
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = os.environ.get("PERF_BASE", "http://localhost:8000")
OUT = Path(__file__).parent / "reports"
SCREENS = {
    "shop": f"{BASE}/perf-org/perf-conf/",
    "control_item_add": f"{BASE}/control/event/perf-org/perf-conf/items/add",
}


def organizer_session():
    """Log in through the real form with Chromium's raw User-Agent (the one Lighthouse's
    headless Chromium will send), so pretix's User-Agent pin accepts the cookie."""
    with sync_playwright() as p:
        browser = p.chromium.launch()
        raw_ua = browser.new_browser_cdp_session().send("Browser.getVersion")["userAgent"]
        page = browser.new_context(user_agent=raw_ua).new_page()
        page.goto(f"{BASE}/control/login")
        page.fill("input[name=email]", "organizer@sqe.test")
        page.fill("input[name=password]", "Sqe-Organizer-2026!")
        page.click("button[type=submit]")
        page.wait_for_url(f"{BASE}/control/")
        cookie = "; ".join(f"{c['name']}={c['value']}" for c in page.context.cookies())
        chrome = p.chromium.executable_path
        browser.close()
    return cookie, chrome, raw_ua


def run(label):
    OUT.mkdir(exist_ok=True)
    cookie, chrome, raw_ua = organizer_session()
    env = dict(os.environ, CHROME_PATH=chrome)
    scores = {}
    for screen, url in SCREENS.items():
        base = OUT / f"lighthouse_{screen}_{label}"
        cmd = ["npx", "--yes", "lighthouse@12", url, "--quiet",
               "--only-categories=accessibility,best-practices",
               "--output=html", "--output=json", f"--output-path={base}", "--preset=desktop",
               "--chrome-flags=--headless=new",
               # pretix pins back-office sessions to the User-Agent (helpers/security.py:97).
               # "--emulatedUserAgent=false" is sent literally as the UA "false" (seen in the
               # pretix log), so pass the exact UA the session was created with.
               f"--emulatedUserAgent={raw_ua}"]
        if screen.startswith("control"):
            cmd.append("--extra-headers=" + json.dumps({"Cookie": cookie}).replace('"', '\\"'))
        subprocess.run(" ".join(f'"{c}"' if " " in c or "{" in c else c for c in cmd),
                       check=True, env=env, shell=True)
        rep = json.loads(Path(f"{base}.report.json").read_text("utf-8"))
        final = rep.get("finalDisplayedUrl") or rep.get("finalUrl")
        if final.split("?")[0] != url:
            raise SystemExit(f"Lighthouse audited {final} instead of {url}; report is invalid")
        scores[screen] = {k: round(v["score"] * 100) for k, v in rep["categories"].items()}
        failed = [a for a in rep["categories"]["accessibility"]["auditRefs"]
                  if rep["audits"][a["id"]]["score"] == 0 and a["weight"] > 0]
        scores[screen]["failed_a11y_audits"] = [a["id"] for a in failed]
        scores[screen]["audited_url"] = final
        print(screen, label, scores[screen], flush=True)
    (OUT / f"lighthouse_scores_{label}.json").write_text(json.dumps(scores, indent=2), "utf-8")


if __name__ == "__main__":
    run(sys.argv[1] if len(sys.argv) > 1 else "before")
