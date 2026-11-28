"""
Screenshots of the public GitHub pages of the team repository (logged-out Chromium, so the pages show exactly what
any reviewer sees). Run IDs and PR numbers are read with the GitHub CLI.

    python docs/sqe/final_report/capture/capture_github.py        (from the repository root)
"""
import json
import re
import subprocess
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

REPO = Path(__file__).resolve().parents[4]
FIG = REPO / "docs/sqe/final_report/figures"
GH = r"C:\Program Files\GitHub CLI\gh.exe"
R = "Zubairilyas1/pretix-sqe"
URL = f"https://github.com/{R}"


def gh_json(*args):
    return json.loads(subprocess.run([GH, *args], capture_output=True, text=True, encoding="utf-8").stdout)


def latest_run(branch, conclusion, event=None):
    """Newest finished run of the current five-gate workflow (runs before 28 Nov used an older workflow)."""
    runs = gh_json("run", "list", "-R", R, "--branch", branch, "-L", "30",
                   "--json", "databaseId,conclusion,event,status,createdAt")
    for r in runs:
        if r["conclusion"] != conclusion or (event and r["event"] != event) or r["createdAt"] < "2026-11-28":
            continue
        jobs = gh_json("run", "view", str(r["databaseId"]), "-R", R, "--json", "jobs")["jobs"]
        if sum(bool(re.match(r"Gate [1-5] - ", j["name"])) for j in jobs) == 5:
            return r["databaseId"]
    return None


def main():
    FIG.mkdir(parents=True, exist_ok=True)
    green = latest_run("zubair", "success", "pull_request")
    red = latest_run("demo/ci-blocked-oversell", "failure")
    fix_runs = gh_json("run", "list", "-R", R, "--branch", "fix/dz01-waitinglist-now-dt", "-L", "10",
                       "--json", "databaseId,conclusion,headSha,displayTitle")
    pages = [
        ("gh_01_repository", f"{URL}/tree/zubair", False),
        ("gh_02_pull_requests", f"{URL}/pulls?q=is%3Apr", False),
        ("gh_03_actions_runs", f"{URL}/actions/workflows/sqe_quality_gate.yml", False),
        ("gh_04_green_run_all_gates", f"{URL}/actions/runs/{green}", True),
        ("gh_05_pr15_checks", f"{URL}/pull/15", True),
        ("gh_06_blocked_pr35", f"{URL}/pull/35", True),
        ("gh_07_blocked_pr35_red_run", f"{URL}/actions/runs/{red}", True),
        ("gh_08_fix_pr36", f"{URL}/pull/36", True),
        ("gh_09_fix_pr36_commits", f"{URL}/pull/36/commits", False),
        ("gh_10_issues", f"{URL}/issues?q=is%3Aissue", True),
        ("gh_11_issue_16_dz01", f"{URL}/issues/16", True),
        ("gh_12_issue_23_w07", f"{URL}/issues/23", True),
        ("gh_13_commits_zubair_branch", f"{URL}/commits/zubair", False),
        ("gh_14_workflow_file", f"{URL}/blob/zubair/.github/workflows/sqe_quality_gate.yml", False),
    ]
    deploy = latest_run("main", "success", "push")
    if deploy:
        pages.append(("gh_16_deploy_run_main", f"{URL}/actions/runs/{deploy}", True))
    for r in fix_runs:
        if r["conclusion"] in ("success", "failure"):                                     # finished runs only
            pages.append((f"gh_15_fix_run_{r['conclusion']}", f"{URL}/actions/runs/{r['databaseId']}", True))
    pages = [pg_ for pg_ in pages if "/runs/None" not in pg_[1]]   # runs that have not finished yet
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1366, "height": 900}, locale="en-US")
        for name, url, full in pages:
            try:
                pg.goto(url, wait_until="load", timeout=60_000)   # GitHub keeps live connections open
                time.sleep(4)
                pg.screenshot(path=str(FIG / f"{name}.png"), full_page=full)
                print("saved", name, url)
            except Exception as e:
                print("FAILED", name, url, e)
        b.close()


if __name__ == "__main__":
    main()
