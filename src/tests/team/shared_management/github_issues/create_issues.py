"""
File every defect of CONSOLIDATED_DEFECT_LOG.md as a GitHub Issue (requires the GitHub CLI, logged in:
`gh auth login`). Idempotent: an issue whose title already exists is skipped.

    python src/tests/team/shared_management/github_issues/create_issues.py --repo Zubairilyas1/pretix-sqe
    python .../create_issues.py --repo Zubairilyas1/pretix-sqe --dry-run

Afterwards the script prints "ID -> #number" lines; put the numbers in the "Issue" column of the defect log.
"""
import argparse
import json
import subprocess
from pathlib import Path

ISSUES = json.loads((Path(__file__).with_name("issues.json")).read_text(encoding="utf-8"))
LABELS = {
    "defect": "d73a4a", "severity:major": "b60205", "severity:minor": "fbca04",
    "priority:P1": "b60205", "priority:P2": "d93f0b", "priority:P3": "c5def5",
    "area:1-whitebox": "0e8a16", "area:2-api": "1d76db", "area:3-e2e-nfr": "5319e7",
    "triage:fix": "0e8a16", "triage:report-upstream": "bfdadc", "triage:accept": "ededed",
}


def gh(*args, check=True):
    return subprocess.run(["gh", *args], capture_output=True, text=True, check=check, encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    if not a.dry_run:
        for name, color in LABELS.items():
            gh("label", "create", name, "--color", color, "--force", "--repo", a.repo)
        existing = {i["title"]: i["number"] for i in json.loads(
            gh("issue", "list", "--repo", a.repo, "--state", "all", "--limit", "500", "--json", "title,number").stdout)}
    else:
        existing = {}
    for it in ISSUES:
        title = f"[{it['id']}] {it['title']}"
        body = (
            f"**Severity:** {it['severity']}  \n**Priority:** {it['priority']}  \n**Status:** {it['status']}  \n"
            f"**Triage decision:** {it['triage']}  \n**Area / found by:** {it['found_by']}  \n"
            f"**Risk register:** {it['risk']}\n\n### Steps to reproduce / evidence\n{it['evidence']}\n\n"
            f"### Expected\n{it['expected']}\n\n### Actual\n{it['actual']}\n\n### Root cause\n{it['root_cause']}\n\n"
            f"### Proposed fix\n{it['fix']}\n"
        )
        if a.dry_run:
            print(title, it["labels"])
            continue
        if title in existing:
            print(f"{it['id']} -> #{existing[title]} (exists)")
            continue
        args = ["issue", "create", "--repo", a.repo, "--title", title, "--body", body]
        for lb in it["labels"]:
            args += ["--label", lb]
        url = gh(*args).stdout.strip()
        number = url.rsplit("/", 1)[-1]
        if it["status"].lower().startswith("fixed"):
            gh("issue", "close", number, "--repo", a.repo, "--reason", "completed",
               "--comment", f"Fixed: {it.get('fixed_by', 'see defect log')}")
        print(f"{it['id']} -> #{number}")


if __name__ == "__main__":
    main()
