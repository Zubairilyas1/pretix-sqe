"""
OWASP ZAP passive scan of W1 and W2, driven by Playwright through the ZAP proxy.

1. ZAP runs in Docker in daemon mode (passive scanning only; no attacks are sent).
2. Playwright (Chromium) is configured with ZAP as its HTTP proxy and walks
   UC-3 (shop -> cart -> checkout -> order page) and the organizer login and
   item editor (W1).
3. After ZAP's passive-scan queue is empty, the alerts are exported to
   evidence/zap_alerts.json and evidence/zap_report.html.

    cd src
    ../.venv/Scripts/python tests/team/tawassul/security/zap_scan.py

The target is the production-like perf server (``perf_server.py``) at its
configured URL http://localhost:8000. Inside the ZAP container a small TCP
forwarder makes localhost:8000 reach the Windows host, and Chromium is told not
to bypass the proxy for loopback addresses, so every request passes ZAP with the
real Host header.
"""
import json
import subprocess
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

ZAP = "http://localhost:8090"
TARGET = "http://localhost:8000"   # pretix's configured URL (perf_pretix.cfg)
EVIDENCE = Path(__file__).parent / "evidence"


def zap(path):
    with urllib.request.urlopen(f"{ZAP}{path}", timeout=30) as r:
        return r.read()


# Runs inside the ZAP container: makes localhost:8000 there reach pretix on the host.
FORWARDER = """
import socket, threading
def pipe(a, b):
    try:
        while (d := a.recv(65536)):
            b.sendall(d)
    except OSError:
        pass
    finally:
        a.close(); b.close()
s = socket.socket(); s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind(('127.0.0.1', 8000)); s.listen(64)
while True:
    c, _ = s.accept(); u = socket.create_connection(('host.docker.internal', 8000))
    threading.Thread(target=pipe, args=(c, u), daemon=True).start()
    threading.Thread(target=pipe, args=(u, c), daemon=True).start()
"""


def start_zap():
    subprocess.run(["docker", "rm", "-f", "sqe-zap"], capture_output=True)
    zap_cmd = ("zap.sh -daemon -silent -host 0.0.0.0 -port 8090 -config api.disablekey=true "
               "-config api.addrs.addr.name=.* -config api.addrs.addr.regex=true")
    subprocess.run(["docker", "run", "-d", "--name", "sqe-zap", "-p", "8090:8090", "zaproxy/zap-stable",
                    "sh", "-c", f"python3 -c \"{FORWARDER}\" & {zap_cmd}"], check=True)
    for _ in range(150):                      # ZAP needs 1-3 minutes on first start
        try:
            print("ZAP", json.loads(zap("/JSON/core/view/version/"))["version"], "ready", flush=True)
            return
        except Exception:
            time.sleep(2)
    raise RuntimeError("ZAP did not start")


def browse():
    with sync_playwright() as p:
        browser = p.chromium.launch(proxy={"server": ZAP, "bypass": "<-loopback>"},
                                    args=["--proxy-bypass-list=<-loopback>"])
        page = browser.new_page()
        # W2 / UC-3 as a customer
        page.goto(f"{TARGET}/perf-org/perf-conf/")
        page.fill("input[name^=item_]", "1")
        page.click("#btn-add-to-cart")
        page.wait_for_load_state("networkidle")
        page.get_by_role("button", name="Proceed with checkout").click()
        page.wait_for_url("**/checkout/questions/**")
        page.fill("input[name=email]", "zap@sqe.test")
        page.click("main form button[type=submit].btn-primary")
        page.check("input[name=payment][value=banktransfer]")
        page.click("main form button[type=submit].btn-primary")
        page.wait_for_url("**/checkout/confirm/")
        page.click("main form button[type=submit].btn-primary")
        try:
            page.wait_for_url("**/order/**", timeout=90_000)
            print("customer flow done: order page reached", flush=True)
        except Exception:                      # passive scan only needs the traffic
            print("customer flow ended at", page.url.split("?")[0], flush=True)
        # W1 as the organizer
        page.goto(f"{TARGET}/control/login")
        page.fill("input[name=email]", "organizer@sqe.test")
        page.fill("input[name=password]", "Sqe-Organizer-2026!")
        page.click("button[type=submit]")
        page.wait_for_url(f"{TARGET}/control/")
        page.goto(f"{TARGET}/control/event/perf-org/perf-conf/items/add")
        page.goto(f"{TARGET}/control/event/perf-org/perf-conf/quotas/")
        browser.close()


def collect():
    while int(json.loads(zap("/JSON/pscan/view/recordsToScan/"))["recordsToScan"]) > 0:
        time.sleep(1)
    alerts = json.loads(zap(f"/JSON/core/view/alerts/?baseurl={TARGET}&start=0&count=9999"))["alerts"]
    EVIDENCE.mkdir(exist_ok=True)
    slim = [{k: a[k] for k in ("pluginId", "alert", "risk", "confidence", "url", "param", "evidence",
                               "cweid", "wascid", "solution")} for a in alerts]
    (EVIDENCE / "zap_alerts.json").write_text(json.dumps(slim, indent=2), "utf-8")
    (EVIDENCE / "zap_report.html").write_bytes(zap("/OTHER/core/other/htmlreport/"))
    by_rule = {}
    for a in slim:
        r = by_rule.setdefault((a["risk"], a["pluginId"], a["alert"]), set())
        r.add(a["url"].split("?")[0])
    order = {"High": 0, "Medium": 1, "Low": 2, "Informational": 3}
    print(f"\n{len(slim)} alert instances, {len(by_rule)} distinct rules")
    for (risk, pid, name), urls in sorted(by_rule.items(), key=lambda kv: (order[kv[0][0]], kv[0][1])):
        print(f"  {risk:<13} {pid:>6}  {name}  ({len(urls)} URLs)")


if __name__ == "__main__":
    start_zap()
    try:
        browse()
        collect()
    finally:
        subprocess.run(["docker", "rm", "-f", "sqe-zap"], capture_output=True)
