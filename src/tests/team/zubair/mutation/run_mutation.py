"""
Real mutation testing of the critical business-rule module with Cosmic Ray.

What it does (nothing is hard-coded - every number comes from the Cosmic Ray session DB):
  1. writes a session config next to the results (test command uses THIS interpreter, so the
     same venv is used on Windows and in CI),
  2. ``cosmic-ray init``      -> enumerates every mutant of src/pretix/base/services/quotas.py,
     using the core operators + the custom operators sqe/SwapAvailabilityVerdict and sqe/SwapOrderStatus,
  3. ``cosmic-ray baseline``  -> the unmutated code must pass the test suite,
  4. ``cosmic-ray exec``      -> runs every mutant; with --workers > 1 it starts that many
     ``cosmic-ray http-worker`` processes, each in its own copy of src/ (PYTHONPATH points at the copy),
  5. writes results/: report.txt (cr-report), report.html (cr-html), summary.json, survivors.json,
  6. exits 1 if the mutation score is below --fail-under (used as the CI quality gate).

Usage (from the repository root):
    python src/tests/team/zubair/mutation/run_mutation.py --workers 6 --fail-under 85
"""
import argparse
import json
import os
import shutil
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[4]                      # .../pretix (contains src/)
MODULE = "src/pretix/base/services/quotas.py"
TESTS = "src/tests/team/zubair"
EXCLUDED_OPERATORS = ["core/RemoveDecorator", "core/VariableInserter"]
CR = [sys.executable, "-m", "cosmic_ray.cli"]


def _posix(p):
    return str(p).replace("\\", "/")


def _free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _write_config(path, worker_urls, timeout):
    test_cmd = (
        f'"{_posix(sys.executable)}" -m pytest -x -q -p no:cacheprovider {TESTS} '
        f"--ignore={TESTS}/test_custom_mutation_operators.py"
    )
    lines = [
        "[cosmic-ray]",
        f'module-path = "{MODULE}"',
        f"timeout = {float(timeout)}",
        "excluded-modules = []",
        f"test-command = '{test_cmd}'",
        "",
        "[cosmic-ray.distributor]",
        f'name = "{"http" if worker_urls else "local"}"',
        "",
    ]
    if worker_urls:
        lines += ["[cosmic-ray.distributor.http]", "worker-urls = [" + ", ".join(f'"{u}"' for u in worker_urls) + "]", ""]
    lines += ["[cosmic-ray.filters.operators-filter]",
              "exclude-operators = [" + ", ".join(f'"{o}"' for o in EXCLUDED_OPERATORS) + "]", ""]
    path.write_text("\n".join(lines))


def _copy_src(dest):
    ignore = shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache", ".coverage*", "node_modules",
                                    "pretix.egg-info")
    shutil.copytree(REPO / "src", dest / "src", ignore=ignore)


def _run(cmd, **kw):
    print("$", " ".join(str(c) for c in cmd), flush=True)
    return subprocess.run(cmd, cwd=REPO, **kw)


def _summarise(db, out):
    con = sqlite3.connect(db)
    rows = con.execute("""
        SELECT ms.job_id, ms.module_path, ms.operator_name, ms.occurrence, ms.start_pos_row, ms.start_pos_col,
               wr.worker_outcome, wr.test_outcome, wr.diff
        FROM mutation_specs ms LEFT JOIN work_results wr ON ms.job_id = wr.job_id
    """).fetchall()
    total = len(rows)
    done = [r for r in rows if r[7] is not None]
    killed = [r for r in done if r[7] == "KILLED"]
    survived = [r for r in done if r[7] == "SURVIVED"]
    incompetent = [r for r in done if r[7] == "INCOMPETENT"]
    by_op = {}
    for r in done:
        op = r[2].split("/")[0] + "/" + r[2].split("/")[1].split("_")[0]
        d = by_op.setdefault(op, {"killed": 0, "survived": 0, "incompetent": 0})
        d[r[7].lower()] += 1
    denominator = len(killed) + len(survived)
    score = round(100.0 * len(killed) / denominator, 2) if denominator else 0.0
    summary = {
        "tool": "cosmic-ray", "module": MODULE, "total_mutants": total, "executed": len(done),
        "killed": len(killed), "survived": len(survived), "incompetent": len(incompetent),
        "mutation_score_percent": score,
        "score_formula": "killed / (killed + survived) * 100 (incompetent mutants excluded)",
        "by_operator": by_op,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=2))
    (out / "survivors.json").write_text(json.dumps([
        {"job_id": r[0], "operator": r[2], "occurrence": r[3], "line": r[4], "col": r[5], "diff": r[8]}
        for r in sorted(survived, key=lambda r: (r[4], r[2]))
    ], indent=2))
    return summary


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=max(1, min(8, (os.cpu_count() or 2) // 2)))
    ap.add_argument("--fail-under", type=float, default=0.0, help="minimum mutation score (percent)")
    ap.add_argument("--timeout", type=float, default=300)
    ap.add_argument("--out", default=str(HERE / "results"))
    ap.add_argument("--report-only", action="store_true", help="re-create reports from an existing session")
    args = ap.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    db = out / "session.sqlite"
    cfg = out / "session.toml"

    if not args.report_only:
        if db.exists():
            db.unlink()
        workers, tmp = [], None
        urls = []
        try:
            if args.workers > 1:
                tmp = Path(tempfile.mkdtemp(prefix="sqe-mut-"))
                for k in range(args.workers):
                    wdir = tmp / f"w{k}"
                    _copy_src(wdir)
                    port = _free_port()
                    env = dict(os.environ, PYTHONPATH=str(wdir / "src"), PYTHONDONTWRITEBYTECODE="1")
                    workers.append(subprocess.Popen(CR + ["http-worker", "--port", str(port)], cwd=wdir, env=env,
                                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))
                    urls.append(f"http://127.0.0.1:{port}")
                time.sleep(5)
            _write_config(cfg, urls, args.timeout)
            if _run(CR + ["init", str(cfg), str(db)]).returncode:
                return 2
            _run([sys.executable, "-m", "cosmic_ray.tools.filters.operators_filter", str(db), str(cfg)])
            base = _run(CR + ["baseline", str(cfg)], capture_output=True, text=True)
            if base.returncode:
                print(base.stdout, base.stderr)
                print("Baseline failed: the unmutated module does not pass the tests.")
                return 2
            t0 = time.time()
            if _run(CR + ["exec", str(cfg), str(db)]).returncode:
                return 2
            print(f"exec finished in {time.time() - t0:.0f} s")
        finally:
            for w in workers:
                w.terminate()
            if tmp:
                shutil.rmtree(tmp, ignore_errors=True)

    rep = _run([sys.executable, "-m", "cosmic_ray.tools.report", str(db), "--show-pending", "--show-diff"],
               capture_output=True, text=True)
    (out / "report.txt").write_text(rep.stdout)
    html = _run([sys.executable, "-c",
                 "import sys; from cosmic_ray.tools.html import report_html; report_html(sys.argv[1:])",
                 str(db)], capture_output=True, text=True)
    (out / "report.html").write_text(html.stdout, encoding="utf-8")
    s = _summarise(db, out)
    keys = ("total_mutants", "executed", "killed", "survived", "incompetent", "mutation_score_percent")
    print(json.dumps({k: s[k] for k in keys}, indent=2))
    if s["mutation_score_percent"] < args.fail_under:
        print(f"MUTATION GATE FAILED: score {s['mutation_score_percent']}% < {args.fail_under}%")
        return 1
    print(f"MUTATION GATE PASSED: score {s['mutation_score_percent']}% >= {args.fail_under}%")
    return 0


if __name__ == "__main__":
    sys.exit(main())
