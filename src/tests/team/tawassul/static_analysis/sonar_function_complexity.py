"""
Measure SonarQube's cyclomatic complexity of ONE function, to compare it with the hand calculation in
cfg_cyclomatic.md. SonarQube's web API reports complexity per file, so the function is copied (unchanged, only
dedented) into a file of its own; the complexity of that file is SonarQube's value for the function.
The critical module quotas.py is scanned in the same run for its file measures.

Needs Docker (SonarQube server) and pysonar (pip). Writes evidence/sonar_function_complexity.json.

    cd src
    ../.venv/Scripts/python tests/team/tawassul/static_analysis/sonar_function_complexity.py
"""
import base64
import inspect
import re
import json
import shutil
import subprocess
import tempfile
import textwrap
import time
import urllib.parse
import urllib.request
from pathlib import Path

HOST = "http://localhost:9010"
IMAGE, SCANNER = "sonarqube:25.1.0.102122-community", "pysonar 1.11.0 (official SonarScanner for Python)"
PROJECT, PW = "sqe-fn-complexity", "Sqe-Fn-Complexity-1"
HERE = Path(__file__).resolve().parent


def call(path, method="GET", data=None, pw=PW):
    req = urllib.request.Request(HOST + path, method=method, data=urllib.parse.urlencode(data).encode() if data else None)
    req.add_header("Authorization", "Basic " + base64.b64encode(f"admin:{pw}".encode()).decode())
    with urllib.request.urlopen(req, timeout=30) as r:
        b = r.read()
        return json.loads(b) if b else {}


def main():
    import django
    import os
    import sys
    sys.path.insert(0, os.getcwd())
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tests.settings")
    django.setup()
    from pretix.base.models import Quota

    work = Path(tempfile.mkdtemp(prefix="sqe-sonar-fn-"))
    (work / "quota_availability_function.py").write_text(
        "# Copied unchanged (dedented) from pretix/base/models/items.py Quota.availability\n"
        + textwrap.dedent(inspect.getsource(Quota.availability)), "utf-8")
    shutil.copy("pretix/base/services/quotas.py", work / "quotas.py")
    # coverage of quotas.py from the Area 1 suite, re-pointed at the copied file
    subprocess.run([sys.executable, "-m", "pytest", "tests/team/zubair", "-q", "-p", "no:cacheprovider",
                    "--ignore=tests/team/zubair/test_custom_mutation_operators.py",
                    "--cov=pretix.base.services.quotas", "--cov-branch", f"--cov-report=xml:{work / 'cov.xml'}"],
                   check=True, capture_output=True)
    xml = (work / "cov.xml").read_text("utf-8")
    xml = re.sub(r"<source>.*?</source>", f"<source>{work.as_posix()}</source>", xml)
    xml = re.sub(r'filename="[^"]*quotas\.py"', 'filename="quotas.py"', xml)
    (work / "cov.xml").write_text(xml, "utf-8")

    subprocess.run(["docker", "rm", "-f", "sqe-sonar-fn"], capture_output=True)
    subprocess.run(["docker", "run", "-d", "--name", "sqe-sonar-fn", "-p", "9010:9000", IMAGE], check=True)
    try:
        for _ in range(120):
            try:
                with urllib.request.urlopen(HOST + "/api/system/status", timeout=5) as r:
                    if json.loads(r.read())["status"] == "UP":
                        break
            except Exception:
                pass
            time.sleep(5)
        call("/api/users/change_password", "POST", {"login": "admin", "previousPassword": "admin", "password": PW}, pw="admin")
        call("/api/projects/create", "POST", {"project": PROJECT, "name": PROJECT})
        token = call("/api/user_tokens/generate", "POST", {"name": "fn", "type": "PROJECT_ANALYSIS_TOKEN",
                                                            "projectKey": PROJECT})["token"]
        # pysonar = official SonarScanner for Python (PyPI); it downloads the scanner engine and the JRE from the
        # SonarQube server itself, so no scanner image is needed.
        pysonar = Path(sys.executable).with_name("pysonar.exe" if os.name == "nt" else "pysonar")
        subprocess.run([str(pysonar), f"--sonar-host-url={HOST}", f"--sonar-token={token}",
                        f"--sonar-project-key={PROJECT}", "--sonar-sources=.", "-Dsonar.python.version=3.11",
                        "-Dsonar.scm.disabled=true", "-Dsonar.python.coverage.reportPaths=cov.xml",
                        "-Dsonar.exclusions=cov.xml", "-Dsonar.qualitygate.wait=true"], check=True, cwd=work)
        tree = call(f"/api/measures/component_tree?component={PROJECT}&qualifiers=FIL&metricKeys="
                    "complexity,cognitive_complexity,ncloc,functions,code_smells,bugs,vulnerabilities,duplicated_lines_density")
        files = {c["path"]: {m["metric"]: m.get("value") for m in c["measures"]} for c in tree["components"]}
        issues = call(f"/api/issues/search?componentKeys={PROJECT}&ps=100")["issues"]
        qkey = f"{PROJECT}:quotas.py"
        keys = ("ncloc,complexity,cognitive_complexity,coverage,line_coverage,branch_coverage,duplicated_lines_density,"
                "code_smells,bugs,vulnerabilities,security_hotspots,sqale_index,sqale_debt_ratio,sqale_rating,"
                "reliability_rating,security_rating")
        quotas_measures = {m["metric"]: m.get("value") for m in
                           call(f"/api/measures/component?component={urllib.parse.quote(qkey)}&metricKeys={keys}")["component"]["measures"]}
        out = {
            "sonarqube": IMAGE, "scanner": SCANNER, "date": time.strftime("%Y-%m-%d %H:%M"),
            "files": files,
            "quotas_py_measures": quotas_measures,
            "issues": [{k: i.get(k) for k in ("component", "rule", "severity", "type", "line", "message")} for i in issues],
        }
        (HERE / "evidence" / "sonar_function_complexity.json").write_text(json.dumps(out, indent=2), "utf-8")
        print(json.dumps(files, indent=2))
        print(json.dumps(quotas_measures, indent=2))
    finally:
        subprocess.run(["docker", "rm", "-f", "sqe-sonar-fn"], capture_output=True)
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    main()
