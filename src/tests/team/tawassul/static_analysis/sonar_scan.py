"""
SonarQube Community static analysis of the W1/W2 source files (Task 3.0).

Starts a throw-away local SonarQube container, scans the four files that
implement the two workflows with sonar-scanner, then exports the project
measures and the issue list to ``evidence/``.

    cd src
    ../.venv/Scripts/python tests/team/tawassul/static_analysis/sonar_scan.py

The container's default admin account is used (local, temporary instance);
SonarQube forces a password change on first use, which the script performs.
"""
import base64
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

SONAR = "http://localhost:9000"
PROJECT = "pretix-sqe-w1w2"
NEW_PASSWORD = "Sqe-Sonar-Local-2026!"
FILES = [
    "pretix/base/services/cart.py",
    "pretix/base/services/orders.py",
    "pretix/base/models/items.py",
    "pretix/control/views/item.py",
]
EVIDENCE = Path(__file__).parent / "evidence"
SRC = Path(__file__).resolve().parents[4]   # .../src


def call(path, method="GET", data=None, password=NEW_PASSWORD):
    req = urllib.request.Request(f"{SONAR}{path}", method=method,
                                 data=urllib.parse.urlencode(data).encode() if data else None)
    req.add_header("Authorization", "Basic " + base64.b64encode(f"admin:{password}".encode()).decode())
    with urllib.request.urlopen(req, timeout=60) as r:
        body = r.read()
        return json.loads(body) if body else {}


def _status():
    try:
        with urllib.request.urlopen(f"{SONAR}/api/system/status", timeout=5) as r:
            return json.loads(r.read())["status"]
    except Exception:
        return None


def start():
    if _status() != "UP":                      # reuse a running instance, else start one
        subprocess.run(["docker", "rm", "-f", "sqe-sonar"], capture_output=True)
        subprocess.run(["docker", "run", "-d", "--name", "sqe-sonar", "-p", "9000:9000", "sonarqube:community"],
                       check=True)
    for _ in range(300):                       # first start can take 5-10 minutes on a laptop
        try:
            with urllib.request.urlopen(f"{SONAR}/api/system/status", timeout=5) as r:
                if json.loads(r.read())["status"] == "UP":
                    break
        except Exception:
            pass
        time.sleep(3)
    else:
        raise RuntimeError("SonarQube did not start")
    try:
        call("/api/users/change_password", "POST",
             {"login": "admin", "previousPassword": "admin", "password": NEW_PASSWORD}, password="admin")
    except urllib.error.HTTPError:
        pass                                   # already changed on an earlier run
    try:
        call("/api/projects/create", "POST", {"project": PROJECT, "name": "pretix W1/W2 (SQE Area 3)"})
    except urllib.error.HTTPError:
        pass                                   # project exists from an earlier run
    return call("/api/user_tokens/generate", "POST", {"name": f"scanner-{int(time.time())}", "type": "PROJECT_ANALYSIS_TOKEN",
                                                      "projectKey": PROJECT})["token"]


def scan(token):
    subprocess.run([
        "docker", "run", "--rm", "-v", f"{SRC}:/usr/src", "sonarsource/sonar-scanner-cli",
        "-Dsonar.host.url=http://host.docker.internal:9000", f"-Dsonar.token={token}",
        f"-Dsonar.projectKey={PROJECT}", "-Dsonar.sources=" + ",".join(FILES),
        "-Dsonar.python.version=3.12", "-Dsonar.scm.disabled=true",
    ], check=True, env=dict(os.environ, MSYS_NO_PATHCONV="1"))
    for _ in range(100):
        tasks = call(f"/api/ce/activity?component={PROJECT}")["tasks"]
        if tasks and tasks[0]["status"] in ("SUCCESS", "FAILED"):
            return tasks[0]["status"]
        time.sleep(3)


def export():
    EVIDENCE.mkdir(exist_ok=True)
    metrics = ("ncloc,complexity,cognitive_complexity,bugs,vulnerabilities,security_hotspots,code_smells,"
               "duplicated_lines_density,sqale_index,reliability_rating,security_rating,sqale_rating")
    project = call(f"/api/measures/component?component={PROJECT}&metricKeys={metrics}")
    files = call(f"/api/measures/component_tree?component={PROJECT}&qualifiers=FIL&ps=50"
                 f"&metricKeys=ncloc,complexity,cognitive_complexity,code_smells,bugs,vulnerabilities")
    issues = call(f"/api/issues/search?componentKeys={PROJECT}&ps=500&s=SEVERITY&asc=false")
    hotspots = {}
    for param in ("project", "projectKey"):      # parameter name differs between versions
        try:
            hotspots = call(f"/api/hotspots/search?{param}={PROJECT}&ps=100")
            break
        except urllib.error.HTTPError:
            continue
    out = {"project": {m["metric"]: m["value"] for m in project["component"]["measures"]},
           "files": {f["path"]: {m["metric"]: m["value"] for m in f["measures"]} for f in files["components"]},
           "issues": [{k: i.get(k) for k in ("rule", "severity", "type", "component", "line", "message", "effort")}
                      for i in issues["issues"]],
           "hotspots": [{k: h.get(k) for k in ("ruleKey", "vulnerabilityProbability", "component", "line", "message")}
                        for h in hotspots.get("hotspots", [])]}
    (EVIDENCE / "sonar_measures.json").write_text(json.dumps(out, indent=2), "utf-8")
    print(json.dumps(out["project"], indent=1))
    print(len(out["issues"]), "issues,", len(out["hotspots"]), "security hotspots")


if __name__ == "__main__":
    if "--export-only" not in sys.argv:
        token = start()
        print("analysis:", scan(token))
    export()
    print("dashboard:", f"{SONAR}/dashboard?id={PROJECT}  (container 'sqe-sonar' left running for screenshots)")
