"""
Console evidence for tools that only print to the terminal (gh, pip-audit, git, k6 summary).

Each command is really executed now; its unmodified output is written to figures/console_<name>.txt and rendered as
an image (monospace text, with the command, working directory, date and commit in the frame) so that it can be
placed in the PDF. The captions in the report say "console output", so it is never presented as a GUI screenshot.

    python docs/sqe/final_report/capture/capture_console.py [name ...]      (from the repository root)
"""
import datetime
import html
import os
import re
import subprocess
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

REPO = Path(__file__).resolve().parents[4]
FIG = REPO / "docs/sqe/final_report/figures"
GH = r"C:\Program Files\GitHub CLI\gh.exe"
R = "Zubairilyas1/pretix-sqe"
PY = str(REPO / ".venv/Scripts/python.exe")
ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")


def failed_log(pr):
    """Last lines of the failing Gate 1 job of a pull request (the pytest summary)."""
    import json
    runs = json.loads(subprocess.run([GH, "run", "list", "-R", R, "--json", "databaseId,event,headBranch,conclusion",
                                      "-L", "40"], capture_output=True, text=True).stdout)
    head = json.loads(subprocess.run([GH, "pr", "view", str(pr), "-R", R, "--json", "headRefName"],
                                     capture_output=True, text=True).stdout)["headRefName"]
    run = next(r for r in runs if r["headBranch"] == head and r["conclusion"] == "failure")
    out = subprocess.run([GH, "run", "view", str(run["databaseId"]), "-R", R, "--log-failed"],
                         capture_output=True, text=True, encoding="utf-8").stdout
    keep = []
    for ln in out.splitlines():
        parts = ln.split("\t", 2)
        if len(parts) < 3 or not parts[0].startswith("Gate 1"):
            continue
        text = re.sub(r"^\d{4}-\d\d-\d\dT[\d:.]+Z ", "", ANSI.sub("", parts[2])).rstrip()
        if re.match(r"^_+ .+ _+$", text) and "coverage:" not in text:   # pytest header of each failing test
            if text.strip("_ "):                         # not the "_ _ _ _" separator lines
                keep.append("FAILED  " + text.strip("_ "))
        elif re.search(r"\d+ failed, \d+ passed", text):
            keep.append(text)
    return f"gh run view {run['databaseId']} -R {R} --log-failed   (Gate 1 job: failing tests and summary)", \
        "\n".join(keep)


def gate5_merge():
    """Merged Gate 5 result of the newest successful run on the zubair branch."""
    import json
    runs = json.loads(subprocess.run([GH, "run", "list", "-R", R, "--branch", "zubair", "-L", "20", "--json",
                                      "databaseId,conclusion,createdAt"], capture_output=True, text=True).stdout)
    run = next(r for r in runs if r["conclusion"] == "success" and r["createdAt"] >= "2026-11-28")
    jobs = json.loads(subprocess.run([GH, "run", "view", str(run["databaseId"]), "-R", R, "--json", "jobs"],
                                     capture_output=True, text=True).stdout)["jobs"]
    job = next(j for j in jobs if j["name"].startswith("Gate 5 -"))
    log = subprocess.run([GH, "api", "--allow-escape-sequences", f"repos/{R}/actions/jobs/{job['databaseId']}/logs"],
                         capture_output=True, text=True, encoding="utf-8").stdout
    keep = [re.sub(r"^\d{4}-\d\d-\d\dT[\d:.]+Z ", "", ANSI.sub("", ln)) for ln in log.splitlines()]
    keep = [ln for ln in keep if re.search(r"merged \d+ shards|total_mutants|executed|killed|survived|pending|"
                                           r"incompetent|score_percent|MUTATION GATE", ln)]
    return (f"gh api repos/{R}/actions/jobs/{job['databaseId']}/logs   (run {run['databaseId']}, job '{job['name']}'; "
            "result lines)"), "\n".join(keep)


COMMANDS = {
    "branch_protection": ([GH, "api", f"repos/{R}/branches/main/protection", "--jq",
                           '"required status checks on main:", (.required_status_checks.checks[] | "  " + .context), '
                           '"required approving reviews: \(.required_pull_request_reviews.required_approving_review_count)", '
                           '"allow force pushes: \(.allow_force_pushes.enabled)", '
                           '"allow deletions: \(.allow_deletions.enabled)"'], REPO),
    "pr35_merge_state": ([GH, "pr", "view", "35", "-R", R, "--json", "number,title,state,mergeStateStatus,statusCheckRollup",
                          "--jq", '"PR #\(.number): \(.title)", "state: \(.state)", "mergeStateStatus: \(.mergeStateStatus)", '
                          '"checks:", (.statusCheckRollup[] | "  \(.name): \(.conclusion)")'], REPO),
    "pr36_checks_per_commit": ([GH, "api", f"repos/{R}/pulls/36/commits", "--jq",
                                ".[] | \"\\(.sha[0:9])  \\(.commit.message | split(\"\\n\")[0])\""], REPO),
    "pip_audit": (["uvx", "pip-audit==2.9.0", "--progress-spinner", "off", "--no-deps", "--disable-pip",
                   "-r", "docs/sqe/final_report/evidence_html/venv_freeze.txt"], REPO),
    "k6_wl1a": (["cmd", "/c", "type", r"results_v2\wl1a.txt"], REPO / "src/tests/team/tawassul/performance"),
    "k6_wl5a": (["cmd", "/c", "type", r"results_v2\wl5a.txt"], REPO / "src/tests/team/tawassul/performance"),
    "git_log_graph": (["git", "log", "--graph", "--oneline", "--decorate", "-25", "--all"], REPO),
    "git_authors": (["git", "shortlog", "-sn", "--no-merges", "c0d887738b6cd97f724b926718c55e2ae87c9901..origin/main", "c0d887738b6cd97f724b926718c55e2ae87c9901..zubair"], REPO),
}


def render(name, cmd_text, cwd, output, pg):
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=REPO, capture_output=True, text=True).stdout.strip()
    stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    (FIG / f"console_{name}.txt").write_text(f"$ {cmd_text}\n{output}", "utf-8")
    page = f"""<html><body style="margin:0;background:#fff">
<div id="c" style="display:inline-block;min-width:760px;max-width:1150px;border:1px solid #444;font-family:Consolas,monospace">
<div style="background:#2d2d2d;color:#ddd;font:12px Segoe UI,Arial;padding:6px 10px">Console output &middot; {html.escape(str(cwd))}</div>
<pre style="margin:0;padding:10px 12px;background:#0c0c0c;color:#e6e6e6;font-size:13px;line-height:1.35;white-space:pre-wrap">
<span style="color:#8ae234">$ {html.escape(cmd_text)}</span>
{html.escape(output.rstrip())}</pre>
<div style="background:#2d2d2d;color:#aaa;font:11px Segoe UI,Arial;padding:4px 10px">captured {stamp} &middot; repository commit {commit}</div>
</div></body></html>"""
    pg.set_content(page)
    pg.locator("#c").screenshot(path=str(FIG / f"console_{name}.png"))
    print("saved console", name)


def main(names):
    FIG.mkdir(parents=True, exist_ok=True)
    if "pip_audit" in names:   # the project's installed packages, without pretix itself (editable, not on PyPI)
        freeze = subprocess.run([PY, "-m", "pip", "freeze", "--exclude-editable"], capture_output=True, text=True).stdout
        if not freeze.strip():
            freeze = subprocess.run(["uv", "pip", "freeze", "--python", PY], capture_output=True, text=True).stdout
        freeze = "\n".join(ln for ln in freeze.splitlines() if not ln.startswith(("-e ", "pretix")))
        (REPO / "docs/sqe/final_report/evidence_html/venv_freeze.txt").write_text(freeze + "\n", "utf-8")
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1600, "height": 900})
        for name in names:
            if name in ("pr35_gate1_failure", "gate5_merge"):
                cmd_text, out = failed_log(35) if name == "pr35_gate1_failure" else gate5_merge()
                render(name, cmd_text, REPO, out, pg)
                continue
            cmd, cwd = COMMANDS[name]
            r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, encoding="utf-8",
                               env={**os.environ, "NO_COLOR": "1"})
            # stderr only matters when the command failed (pip-audit prints its result line there)
            err = r.stderr if (r.returncode != 0 or name == "pip_audit") else ""
            out = ANSI.sub("", r.stdout + (("\n" + err) if err.strip() else ""))
            shown = " ".join(Path(c).name if i == 0 else (f"'{c}'" if (" " in c or '"' in c) else c)
                             for i, c in enumerate(cmd))
            render(name, shown, cwd, out, pg)
        b.close()


if __name__ == "__main__":
    main(sys.argv[1:] or list(COMMANDS) + ["pr35_gate1_failure"])
