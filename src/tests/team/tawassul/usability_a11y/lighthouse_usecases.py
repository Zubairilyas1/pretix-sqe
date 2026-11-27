"""
Lighthouse (accessibility, best practices, SEO) AND a full axe-core scan on the key screen of every use case,
with one shared browser session per role, then one de-duplicated findings table (an issue found by both tools is
counted once).

Prerequisites (see performance/k6_metrics_report.md "How to reproduce"): perf server running on PERF_BASE,
seed_perf_event.py and seed_uc_screens.py executed.

    cd src
    ../.venv/Scripts/python tests/team/tawassul/usability_a11y/lighthouse_usecases.py

Outputs in reports/usecases/: lighthouse_<uc>.report.{html,json}, axe_<uc>.json, summary.json, findings.md
"""
import json
import os
import re
import subprocess
from pathlib import Path

from axe_playwright_python.sync_playwright import Axe
from playwright.sync_api import sync_playwright

BASE = os.environ.get("PERF_BASE", "http://localhost:8000")
HERE = Path(__file__).parent
OUT = HERE / "reports" / "usecases"
ORDER = json.loads((HERE / "reports" / "uc_screens.json").read_text("utf-8"))
E = "/perf-org/perf-conf"
SCREENS = [  # (id, use case, role, url, description)
    ("uc1", "UC-1 configure item and quota", "organizer", f"{BASE}/control/event{E}/items/add", "Create a new product"),
    ("uc2", "UC-2 publish event / sales window", "organizer", f"{BASE}/control/event{E}/live/", "Shop status (go live)"),
    ("uc3", "UC-3 checkout", "customer", f"{BASE}{E}/checkout/questions/", "Checkout - your information"),
    ("uc4", "UC-4 apply voucher", "customer", f"{BASE}{E}/redeem?voucher=SQE-VOUCHER-1", "Voucher redemption"),
    ("uc5", "UC-5 sold-out category", "customer", f"{BASE}{E}/", "Shop page with a sold-out product"),
    ("uc6", "UC-6 cancel pending order", "customer",
     f"{BASE}{E}/order/{ORDER['order_code']}/{ORDER['order_secret']}/cancel", "Cancel order"),
]
WCAG_AA = {"runOnly": {"type": "tag", "values": ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"]}}
FIX = {
    "color-contrast": "Darken the text/foreground colour to reach a contrast ratio of at least 4.5:1 (3:1 for large text).",
    "aria-input-field-name": "Give the combobox an accessible name (aria-labelledby pointing at the visible label).",
    "label": "Associate a <label for> (or aria-label) with the form control.",
    "link-name": "Add discernible text or an aria-label to the link.",
    "image-alt": "Add an alt attribute (empty for decorative images).",
    "html-has-lang": "Add lang to <html>.",
    "heading-order": "Use heading levels in sequence (do not skip levels).",
    "landmark-one-main": "Wrap the main content in a single <main> landmark.",
    "region": "Place all content inside landmarks.",
    "meta-description": "Add a <meta name=description> with a summary of the page.",
    "is-crawlable": "Intended: back-office and personal order pages are noindex on purpose (no fix).",
    "errors-in-console": "Fix the JavaScript/network error reported in the console.",
    "inspector-issues": "Fix the issue reported in the Chrome DevTools Issues panel (often cookie or CSP warnings).",
    "link-text": "Use descriptive link text instead of generic words.",
    "crawlable-anchors": "Use real hrefs on anchors (not '#' or javascript:).",
    "label-content-name-mismatch": "Make the accessible name contain the visible label text.",
    "select-name": "Give the <select> a label.",
    "button-name": "Give the button discernible text or aria-label.",
    "aria-allowed-attr": "Remove ARIA attributes the role does not support.",
    "list": "Only put <li> elements directly inside <ul>/<ol>.",
    "frame-title": "Add a title to the iframe.",
    "duplicate-id-aria": "Make ids referenced by ARIA unique.",
}


def login(browser, ua):
    ctx = browser.new_context(user_agent=ua)
    page = ctx.new_page()
    page.goto(f"{BASE}/control/login")
    page.fill("input[name=email]", "organizer@sqe.test")
    page.fill("input[name=password]", "Sqe-Organizer-2026!")
    page.click("button[type=submit]")
    page.wait_for_url(re.compile(r"/control/(?!login)"))
    return ctx, page


def customer(browser, ua):
    ctx = browser.new_context(user_agent=ua)
    page = ctx.new_page()
    page.goto(f"{BASE}{E}/")
    page.locator("input[name^=item_]").first.fill("1")
    page.click("#btn-add-to-cart")
    page.wait_for_load_state("networkidle")
    return ctx, page


def norm(sel):
    if isinstance(sel, list):
        sel = " ".join(str(s) for s in sel)
    return re.sub(r"\s+", " ", str(sel or "")).strip()


def match_key(sel):
    """axe reports short selectors (#id, .class), Lighthouse full paths (div > span#id). Both name the same
    element when the LAST simple selector agrees after dropping the tag name."""
    last = re.split(r"\s*>\s*|\s+", sel.strip())[-1] if sel else ""
    return re.sub(r"^[a-z][a-z0-9]*(?=[#.:\[])", "", last)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    summary, findings = {}, {}
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ua = browser.new_browser_cdp_session().send("Browser.getVersion")["userAgent"]
        sessions = {"organizer": login(browser, ua), "customer": customer(browser, ua)}
        chrome = p.chromium.executable_path
        for sid, uc, role, url, desc in SCREENS:
            ctx, page = sessions[role]
            # ---- axe on the same screen with the same session ----
            page.goto(url)
            page.wait_for_load_state("networkidle")
            if page.url.split("?")[0] != url.split("?")[0]:
                raise SystemExit(f"{sid}: browser ended on {page.url} instead of {url}")
            axe = Axe().run(page, options=WCAG_AA).response["violations"]
            (OUT / f"axe_{sid}.json").write_text(json.dumps({"url": page.url, "violations": [
                {"rule": v["id"], "impact": v["impact"], "help": v["help"], "helpUrl": v["helpUrl"],
                 "nodes": [norm(n["target"]) for n in v["nodes"]]} for v in axe]}, indent=2), "utf-8")
            # ---- Lighthouse with the cookies of that session ----
            cookie = "; ".join(f"{c['name']}={c['value']}" for c in ctx.cookies())
            base = OUT / f"lighthouse_{sid}"
            cmd = ["npx", "--yes", "lighthouse@12", url, "--quiet",
                   "--only-categories=accessibility,best-practices,seo",
                   "--output=html", "--output=json", f"--output-path={base}", "--preset=desktop",
                   "--chrome-flags=--headless=new", f"--emulatedUserAgent={ua}",
                   "--extra-headers=" + json.dumps({"Cookie": cookie}).replace('"', '\\"')]
            subprocess.run(" ".join(f'"{c}"' if (" " in c or "{" in c or "&" in c or "?" in c) else c for c in cmd),
                           check=True, env=dict(os.environ, CHROME_PATH=chrome), shell=True)
            rep = json.loads(Path(f"{base}.report.json").read_text("utf-8"))
            final = rep.get("finalDisplayedUrl") or rep.get("finalUrl")
            if final.split("?")[0] != url.split("?")[0]:
                raise SystemExit(f"{sid}: Lighthouse audited {final} instead of {url}; report invalid")
            scores = {k: round(v["score"] * 100) for k, v in rep["categories"].items()}
            summary[sid] = {"use_case": uc, "screen": desc, "url": final, "lighthouse": scores,
                            "axe_rules_violated": len(axe), "axe_elements": sum(len(v["nodes"]) for v in axe)}
            print(sid, scores, "axe:", len(axe), flush=True)
            # ---- merge: key = (rule, element) ----
            for v in axe:
                for n in v["nodes"]:
                    k = (v["id"], match_key(norm(n["target"])))
                    f = findings.setdefault(k, {"rule": v["id"], "element": norm(n["target"]), "screens": set(),
                                                "found_by": set(), "impact": v["impact"], "help": v["help"]})
                    f["screens"].add(sid)
                    f["found_by"].add("axe")
            for cat in ("accessibility", "best-practices", "seo"):
                for ref in rep["categories"][cat]["auditRefs"]:
                    a = rep["audits"][ref["id"]]
                    if a.get("score") is None or a["score"] == 1 or ref.get("weight", 0) == 0:
                        continue
                    items = (a.get("details") or {}).get("items") or [{}]
                    for it in items:
                        node = it.get("node") or {}
                        el = norm(node.get("selector")) or norm(it.get("source", {}).get("url") if isinstance(it.get("source"), dict) else "") or "(page)"
                        k = (ref["id"], match_key(el) if node else el)
                        f = findings.setdefault(k, {"rule": ref["id"], "element": el, "screens": set(), "found_by": set(),
                                                    "impact": "serious" if cat == "accessibility" else cat, "help": a["title"]})
                        f["screens"].add(sid)
                        f["found_by"].add(f"Lighthouse ({cat})")
        browser.close()
    rows = sorted(findings.values(), key=lambda f: (f["rule"], f["element"]))
    (OUT / "summary.json").write_text(json.dumps({"screens": summary, "findings": [
        {**f, "screens": sorted(f["screens"]), "found_by": sorted(f["found_by"])} for f in rows]}, indent=2), "utf-8")
    md = ["| # | Rule / audit | Element | Screens | Found by | User impact | Proposed fix |",
          "| :-: | :--- | :--- | :--- | :--- | :--- | :--- |"]
    for i, f in enumerate(rows, 1):
        both = "axe" in f["found_by"] and any(x.startswith("Lighthouse") for x in f["found_by"])
        by = "**both** (counted once)" if both else ", ".join(sorted(f["found_by"]))
        el = f["element"].replace("|", "\\|")[:90]
        md.append(f"| {i} | `{f['rule']}` | `{el}` | {', '.join(sorted(f['screens']))} | {by} | "
                  f"{f['impact']}: {f['help']} | {FIX.get(f['rule'], 'See the audit help: ' + f['help'])} |")
    md += ["", "| Screen | Use case | Accessibility | Best practices | SEO | axe rules / elements |",
           "| :--- | :--- | :-: | :-: | :-: | :-: |"]
    for sid, s in summary.items():
        sc = s["lighthouse"]
        md.append(f"| {sid}: {s['screen']} | {s['use_case']} | {sc.get('accessibility')} | {sc.get('best-practices')} | "
                  f"{sc.get('seo')} | {s['axe_rules_violated']} / {s['axe_elements']} |")
    (OUT / "findings.md").write_text("\n".join(md) + "\n", "utf-8")
    print("written", OUT / "findings.md")


if __name__ == "__main__":
    main()
