#!/usr/bin/env python3
"""Run the auto-II harness (auto_ii.py) over elements top-down (tput-gate-1010, owner 2026-10-11).

For each element: its newest CLOSED closure-loop job (else the newest job with a passing exact bench) gives the source
commit and the exact bench command; the commit's sources are extracted to a work dir, the bench is recorded through the
iverilog shim, and the stream is measured (recorded-dense or replayed back-to-back).  One JSON a element is written to
--out (committed as the record: job, commit, bench, verdict, II).  Elements are ranked by the budget's critical weight.

    python3 tools/throughput_budget/auto_ii_batch.py --budget results/arch/throughput_budget_20261010/budget.json \
        --work /srv/.../autoii --out results/arch/throughput_budget_20261010/auto_ii [--limit 20] [-j 4]
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import glob
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
JOBS = Path.home() / ".local/state/closure_loop/jobs"
PATHS = ["tools", "rtl", "physical/asap7_memory_macros", ":(glob)physical/hbm_accel_die_views/*/rtl/**",
         ":(glob)physical/*/rtl/**", "compiler/models"]


def jobs_by_block():
    out = {}
    for f in glob.glob(str(JOBS / "*.json")):
        try:
            j = json.loads(open(f).read())
        except Exception:  # noqa: BLE001
            continue
        b = (j.get("spec") or {}).get("block")
        benches = [x for x in ((j.get("spec") or {}).get("stages") or {}).get("bench") or [] if x.get("expect") == "pass"]
        if not b or not benches:
            continue
        ok = any(v.get("ok") and v.get("expect") == "pass" for v in (j.get("benches") or {}).values())
        if not ok:
            continue
        key = (j.get("status") == "CLOSED", j.get("updated", 0))
        if b not in out or key > out[b][0]:
            out[b] = (key, j, benches)
    return {b: (j, bs) for b, (_, j, bs) in out.items()}


def run_one(block, j, benches, work, out, timeout, src_root=None):
    commit = j.get("commit_full") or j["spec"]["source"]["commit"]
    d = Path(work) / block
    shutil.rmtree(d, ignore_errors=True)
    src = d / "src"
    (d / "run").mkdir(parents=True)
    if src_root:      # run the element's bench on a checkout (current main): a per-element symlink farm keeps writes local
        subprocess.run(["cp", "-rs", str(Path(src_root).resolve()), str(src)], check=True)
        commit = subprocess.run(["git", "-C", str(src_root), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    else:
        src.mkdir(parents=True)
        extra = list((j["spec"].get("source") or {}).get("extra_paths") or [])
        ar = subprocess.run(["git", "-C", str(ROOT), "archive", commit, "--"] + PATHS + extra, capture_output=True)
        if ar.returncode:
            ar = subprocess.run(["git", "-C", str(ROOT), "archive", commit, "--", "tools", "rtl"] + extra, capture_output=True)
        subprocess.run(["tar", "-x", "-C", str(src)], input=ar.stdout)
    res = dict(block=block, job=j["name"], commit=commit[:9], job_commit=(j.get("commit_full") or "")[:9],
               status_job=j.get("status"), source="checkout" if src_root else "job commit archive")
    for b in benches:
        cmd = b["cmd"].replace("{RUN}", str(d / "run")).replace("{SRC}", str(src)).replace("{NAME}", j["name"]) \
            .replace("{CL}", str(d / "cl")).replace("{THREADS}", "4").replace("{HOST}", "local")
        rr = d / ("aii_" + re.sub(r"\W", "_", b["name"]))
        p = subprocess.run([sys.executable, str(HERE / "auto_ii.py"), "record", "--block", block, "--run", str(rr),
                            "--timeout", str(timeout), "--", "bash", "-c", cmd], cwd=src, capture_output=True, text=True,
                           timeout=timeout + 60)
        if '"recorded": true' not in p.stdout:
            res.setdefault("tried", []).append(dict(bench=b["name"], recorded=False, tail=(p.stdout + p.stderr)[-300:]))
            continue
        q = subprocess.run([sys.executable, str(HERE / "auto_ii.py"), "replay", "--run", str(rr), "--timeout", str(timeout)],
                           cwd=src, capture_output=True, text=True, timeout=timeout + 60)
        try:
            a = json.loads((rr / "autoii.json").read_text())
        except Exception:  # noqa: BLE001
            res.setdefault("tried", []).append(dict(bench=b["name"], recorded=True, replay_error=(q.stdout + q.stderr)[-300:]))
            continue
        a.update(bench=b["name"], bench_cmd=b["cmd"][:300])
        res["auto_ii"] = a
        break
    shutil.rmtree(src, ignore_errors=True)                     # sources are the commit; keep only the records
    for v in d.glob("aii_*/autoii.vcd"):
        v.unlink(missing_ok=True)
    res["verdict"] = (res.get("auto_ii") or {}).get("verdict") or "NOT_RECORDED (bench not iverilog / instance not found)"
    Path(out).mkdir(parents=True, exist_ok=True)
    (Path(out) / f"{block}.json").write_text(json.dumps(res, indent=1) + "\n")
    return res


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--budget")
    ap.add_argument("--work", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("-j", type=int, default=4)
    ap.add_argument("--timeout", type=int, default=1800)
    ap.add_argument("--blocks", nargs="*")
    ap.add_argument("--src-root", help="run benches on this checkout (fleet: current main) instead of per-commit archives")
    ap.add_argument("--plan-out", help="write the todo list (from the local closure-loop state) and exit")
    ap.add_argument("--plan-in", help="read the todo list (on a fleet host)")
    a = ap.parse_args()
    if a.plan_in:
        plan = json.loads(Path(a.plan_in).read_text())
        todo = [(x["block"], x["job"], x["benches"]) for x in plan["todo"]]
        want = [x["block"] for x in plan["todo"]]
    else:
        bud = json.loads(Path(a.budget).read_text())
        els = bud["elements"]
        want = a.blocks or [e for e, v in els.items() if v["status"] in ("UNQUALIFIED_NO_BENCH",)]
        jb = jobs_by_block()
        todo = [(e, *jb[e]) for e in want if e in jb]
        if a.plan_out:
            Path(a.plan_out).write_text(json.dumps(dict(todo=[dict(block=e, job={k: j[k] for k in ("name", "status", "commit_full", "spec")
                                                                                  if k in j}, benches=bs) for e, j, bs in todo]), indent=1))
            print("plan", len(todo))
            return 0
    if a.limit:
        todo = todo[:a.limit]
    print(f"{len(want)} candidates, {len(todo)} with a passing exact closure-loop bench", flush=True)
    with cf.ThreadPoolExecutor(a.j) as ex:
        futs = {ex.submit(run_one, e, j, bs, a.work, a.out, a.timeout, a.src_root): e for e, j, bs in todo}
        for f in cf.as_completed(futs):
            try:
                r = f.result()
                print(r["block"], r["verdict"], (r.get("auto_ii") or {}).get("ii"), flush=True)
            except Exception as ex_:  # noqa: BLE001
                print(futs[f], "ERROR", ex_, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
