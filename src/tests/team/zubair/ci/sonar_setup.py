"""
Prepare a fresh SonarQube server for the CI quality gate and export the measures afterwards.

  python sonar_setup.py --coverage-threshold 99      -> prints SONAR_TOKEN=<token> (for $GITHUB_ENV)
  python sonar_setup.py --export sonar-measures.json -> writes measures + quality gate status

The quality gate "SQE Area1 Gate" is created on OVERALL code (a new project has no "new code"
period yet, so the default "Sonar way" gate would pass trivially). Conditions - justified in
docs/sqe/zubair/CI_QUALITY_GATE_REPORT.md:
  coverage                  < threshold  -> ERROR
  reliability_rating        > 1 (A)      -> ERROR   (any bug)
  security_rating           > 1 (A)      -> ERROR   (any vulnerability)
  sqale_rating              > 1 (A)      -> ERROR   (technical-debt ratio above 5 %)
  duplicated_lines_density  > 3          -> ERROR
"""
import argparse
import base64
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request

HOST = "http://localhost:9000"
PROJECT = "pretix-sqe-quotas"
GATE = "SQE Area1 Gate"
DEFAULT_PW, NEW_PW = "admin", "Sqe-Ci-Only-Password-1"


def call(path, method="GET", data=None, password=NEW_PW):
    req = urllib.request.Request(HOST + path, method=method,
                                 data=urllib.parse.urlencode(data).encode() if data else None)
    req.add_header("Authorization", "Basic " + base64.b64encode(f"admin:{password}".encode()).decode())
    with urllib.request.urlopen(req, timeout=30) as r:
        body = r.read()
        return json.loads(body) if body else {}


def wait_up(limit=600):
    t0 = time.time()
    while time.time() - t0 < limit:
        try:
            with urllib.request.urlopen(HOST + "/api/system/status", timeout=10) as r:
                if json.loads(r.read())["status"] == "UP":
                    return
        except (urllib.error.URLError, ConnectionError, KeyError, ValueError):
            pass
        time.sleep(5)
    raise SystemExit("SonarQube did not come up")


def setup(threshold):
    wait_up()
    try:
        call("/api/users/change_password", "POST",
             {"login": "admin", "previousPassword": DEFAULT_PW, "password": NEW_PW}, password=DEFAULT_PW)
    except urllib.error.HTTPError as e:
        if e.code != 401:  # 401 = already changed on a reused server
            raise
    call("/api/projects/create", "POST", {"project": PROJECT, "name": PROJECT})
    gate = call("/api/qualitygates/create", "POST", {"name": GATE})
    gate_name = gate.get("name", GATE)
    for metric, op, err in [
        ("coverage", "LT", threshold),
        ("reliability_rating", "GT", "1"),
        ("security_rating", "GT", "1"),
        ("sqale_rating", "GT", "1"),
        ("duplicated_lines_density", "GT", "3"),
    ]:
        call("/api/qualitygates/create_condition", "POST",
             {"gateName": gate_name, "metric": metric, "op": op, "error": err})
    call("/api/qualitygates/select", "POST", {"gateName": gate_name, "projectKey": PROJECT})
    token = call("/api/user_tokens/generate", "POST",
                 {"name": f"ci-{int(time.time())}", "type": "PROJECT_ANALYSIS_TOKEN", "projectKey": PROJECT})["token"]
    env_file = os.environ.get("GITHUB_ENV")
    if env_file:  # GitHub Actions: hide the token in logs and pass it to the next step
        print(f"::add-mask::{token}")
        with open(env_file, "a") as f:
            f.write(f"SONAR_TOKEN={token}\n")
    else:
        print(f"SONAR_TOKEN={token}")
    print("SonarQube ready: project", PROJECT, "gate", gate_name)


def export(path):
    metrics = ("ncloc,complexity,cognitive_complexity,coverage,line_coverage,branch_coverage,"
               "duplicated_lines_density,code_smells,bugs,vulnerabilities,security_hotspots,"
               "sqale_index,sqale_rating,reliability_rating,security_rating,alert_status")
    m = call(f"/api/measures/component?component={PROJECT}&metricKeys={metrics}")
    gate = call(f"/api/qualitygates/project_status?projectKey={PROJECT}")
    issues = call(f"/api/issues/search?componentKeys={PROJECT}&ps=500")
    funcs = call(f"/api/measures/component_tree?component={PROJECT}&metricKeys=complexity,cognitive_complexity"
                 f"&qualifiers=FIL")
    out = {
        "measures": {x["metric"]: x.get("value") for x in m["component"]["measures"]},
        "quality_gate": gate["projectStatus"],
        "issues": [{k: i.get(k) for k in ("rule", "severity", "type", "line", "message", "effort")}
                   for i in issues.get("issues", [])],
        "files": {c["path"]: {x["metric"]: x.get("value") for x in c.get("measures", [])}
                  for c in funcs.get("components", [])},
    }
    with open(path, "w") as f:
        json.dump(out, f, indent=2)
    print(json.dumps(out["measures"], indent=2))
    print("quality gate:", out["quality_gate"]["status"])


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--coverage-threshold", default="99")
    ap.add_argument("--export")
    a = ap.parse_args()
    if a.export:
        export(a.export)
    else:
        setup(a.coverage_threshold)
