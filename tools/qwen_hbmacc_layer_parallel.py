#!/usr/bin/env python3
"""HA8: layer-parallel exact full token of the Qwen3-8B HBM accelerator (tools/qwen_hbmacc_rt_token_w12.py jobs).

Method (as tools/qwen_rom_layer_parallel_sim.py for the ROM): every stage (L0..L35, head) runs as its own job,
entered from the golden checkpoint at position P:
    job L0:   X = x_preload(token[P]);            job Lk: X = golden exit of L(k-1);   head: golden exit of L35
    every layer job loads its layer's KV window of positions < P (the oracle's kv_pre) into the KV memory;
    check RTL exit == golden exit bit-exactly on every die (head: token id and logit bits).
Because golden exit(k-1) is the input of golden stage k, the stage proofs compose into the full token.  The
host is the HA8 host (the pinned W12 host's memory semantics: every stage starts from its sequencer's start,
the vector memory outside X is the stage's own writes; the pinned W12 composition evidence of
results/rtl/qwen_rom_layer_parallel_20261003 applies to the same datapath).

TIMING.  In the chained token the prefetch stream never pauses at a stage boundary (weights and the KV of
positions < P do not depend on the token), so a stage starts with the words the stream fetched during the
previous stage's tail.  Each isolated job reproduces that with --preroll (controller cycles the stream runs
before the core's first edge): the measured tail of the previous stage (cycles after its last code-word read).
The composed token is 7 + sum(stage cycles) + (stages - 1), as the ROM tool composes it.

    --plan     job dirs (stages.txt, preload.hex) under --plan-dir
    --run      run (or resume) every job: a pool of --parallel jobs, each through admit.sh
    --verify   exactness of every stage, the composed cycles and the per-stage attribution -> verdict.json
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORE_HZ = 1.2e9


def stage_names():
    return [f"L{n}" for n in range(36)] + ["head"]


def cmd_plan(a):
    pdir = a.plan_dir.resolve()
    pdir.mkdir(parents=True, exist_ok=True)
    stages = {l.split()[0]: l.split() for l in a.stages.read_text().splitlines() if l.strip()}
    orc = a.oracle_dir.resolve()
    jobs = []
    for i, name in enumerate(stage_names()):
        if a.only and name not in a.only.split(","):
            continue
        j = pdir / name
        j.mkdir(exist_ok=True)
        (j / "stages.txt").write_text(" ".join(stages[name]) + "\n")
        src = orc / "x_preload.hex" if i == 0 else orc / f"L{i - 1:02d}_die0_x.hex"
        words = [w for w in src.read_text().split() if not w.startswith("@")]
        if len(words) != 4096:
            raise SystemExit(f"{src}: {len(words)} words")
        (j / "preload.hex").write_text("@1000\n" + "\n".join(words) + "\n")
        jobs.append(name)
    plan = {"schema": "opentallas.hbm-accel-ha8-layer-parallel-plan.v1", "jobs": jobs, "oracle_dir": str(orc),
            "stages": str(a.stages), "pos": a.pos, "token": a.token, "layout": str(a.layout), "build_dir": str(a.build_dir),
            "driver_args": a.driver_args, "preroll": a.preroll, "preroll_stage": a.preroll_stage, "at": time.strftime("%FT%TZ", time.gmtime())}
    (pdir / "plan.json").write_text(json.dumps(plan, indent=1) + "\n")
    print(f"planned {len(jobs)} jobs in {pdir}")


def run_job(pdir: Path, plan: dict, name: str, a) -> int:
    j = pdir / name
    if (j / "token_result.json").exists() and not a.force:
        return 0
    over = dict(kv.split("=") for kv in plan.get("preroll_stage", "").split(",") if kv)
    pre = int(over[name]) if name in over else (plan["preroll"] if name != "head" else 0)
    cmd = [a.admit, str(a.peak_gb), "--", sys.executable, str(ROOT / "tools/qwen_hbmacc_rt_token_w12.py"),
           "--workdir", str(j), "--build-dir", plan["build_dir"], "--stages", str(j / "stages.txt"),
           "--layout", plan["layout"], "--oracle-dir", plan["oracle_dir"], "--preload", str(j / "preload.hex"),
           "--pos", str(plan["pos"]), "--token", str(plan["token"]), "--preroll", str(pre), "--threads", str(a.threads),
           *plan["driver_args"].split()]
    if name != "head" and plan["pos"]:
        cmd += ["--kv-dir", str(Path(plan["oracle_dir"]) / "kv_pre")]
    (j / "cmd.txt").write_text(" ".join(cmd) + "\n")
    t0 = time.time()
    with open(j / "driver.log", "w") as log:
        rc = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT).returncode
    (j / "exit.json").write_text(json.dumps({"rc": rc, "wall_s": round(time.time() - t0, 1)}) + "\n")
    return rc


def cmd_run(a):
    pdir = a.plan_dir.resolve()
    plan = json.loads((pdir / "plan.json").read_text())
    names = [n for n in plan["jobs"] if not a.only or n in a.only.split(",")]
    with ThreadPoolExecutor(a.parallel) as ex:
        rcs = list(ex.map(lambda n: run_job(pdir, plan, n, a), names))
    print(dict(zip(names, rcs)))


def cmd_verify(a):
    pdir = a.plan_dir.resolve()
    plan = json.loads((pdir / "plan.json").read_text())
    rows, exact, total, missing = {}, True, 7, []
    cats = ("hbm_wait", "kv_wait", "matmul", "attention", "collective", "stream_unit", "other")
    agg = {c: 0 for c in cats}
    for name in stage_names():
        f = pdir / name / "token_result.json"
        if not f.exists():
            missing.append(name); exact = False
            continue
        r = json.loads(f.read_text())
        st = r["stages"][name]
        d0 = st.get("die0", {})
        ok = r["status"] == "pass"
        exact &= ok
        cyc = st["cycles"]
        total += cyc
        for c in cats:
            agg[c] += d0.get(c, 0)
        rows[name] = {"status": r["status"], "cycles": cyc, "die0": d0,
                      "x_mismatches": sum(c["mismatches"] for c in r["layer_x_checks"].values()),
                      "rtl_token": r.get("rtl_token"), "rtl_logit_bits": r.get("rtl_logit_bits"),
                      "tail_after_last_wread": (st["end_cyc"] - d0["last_wread_cyc"]) if d0.get("last_wread_cyc") else None,
                      "wall_s": r["simulate_wall_seconds"]}
    total += len(stage_names()) - 1
    head = rows.get("head", {})
    verdict = {"schema": "opentallas.hbm-accel-ha8-layer-parallel-verdict.v1", "plan": plan,
               "composed_full_token_exact": exact and not missing, "missing": missing,
               "token": head.get("rtl_token"), "logit_bits": head.get("rtl_logit_bits"),
               "composed_cycles": total if not missing else None,
               "composed_us": round(total / CORE_HZ * 1e6, 2) if not missing else None,
               "ar_tok_s": round(CORE_HZ / total, 1) if not missing else None,
               "attribution_die0_cycles": agg, "stages": rows}
    (pdir / "verdict.json").write_text(json.dumps(verdict, indent=1) + "\n")
    print(json.dumps({k: verdict[k] for k in ("composed_full_token_exact", "missing", "token", "logit_bits", "composed_cycles",
                                              "composed_us", "ar_tok_s", "attribution_die0_cycles")}, indent=1))


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--plan", action="store_true")
    g.add_argument("--run", action="store_true")
    g.add_argument("--verify", action="store_true")
    ap.add_argument("--plan-dir", type=Path, required=True)
    ap.add_argument("--stages", type=Path, help="full stage list (L0..L35, head) of the W12 images")
    ap.add_argument("--oracle-dir", type=Path)
    ap.add_argument("--layout", type=Path)
    ap.add_argument("--build-dir", type=Path)
    ap.add_argument("--pos", type=int, default=0)
    ap.add_argument("--token", type=int, default=0)
    ap.add_argument("--preroll", type=int, default=0)
    ap.add_argument("--preroll-stage", default="", help="per-stage preroll overrides, e.g. L0=5000,L1=5000")
    ap.add_argument("--driver-args", default="", help="extra tools/qwen_hbmacc_rt_token_w12.py design-point flags")
    ap.add_argument("--only", help="comma-separated stage names")
    ap.add_argument("--parallel", type=int, default=8)
    ap.add_argument("--threads", type=int, default=4)
    ap.add_argument("--peak-gb", type=int, default=16)
    ap.add_argument("--admit", default="/srv/opentallas-scratch/admit.sh")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    {"plan": cmd_plan, "run": cmd_run, "verify": cmd_verify}[[k for k in ("plan", "run", "verify") if getattr(a, k)][0]](a)


if __name__ == "__main__":
    main()
