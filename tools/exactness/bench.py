#!/usr/bin/env python3
"""Run ONE end-to-end exactness bench from this source tree (on a fleet host) and write WORK/result.json.

Every bench rebuilds its RTL from the tree this file lives in; fixtures (golden X/KV, stage images, captured
inputs) are read from their retained fleet paths and never regenerated.  result.json always carries
{"bench", "exact": bool, "cycles": int|None, ...bench fields}.  The orchestrator (tools/exactness/regress.py)
compares it with tools/exactness/benches.json.

    bench.py BENCH --work DIR
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "tools"
PY = sys.executable
S = Path("/srv/opentallas-scratch")
S2 = Path("/srv/opentallas-scratch2")
# reduced-vehicle goldens need `tokenizers` (V4.1 Engram token map): a venv on the bench host carries it
VENV = S / "claude/exactness/venv/bin/python"
HPY = str(VENV) if VENV.exists() else PY


def save(work, rec):
    (work / "result.json").write_text(json.dumps(rec, indent=1, default=str) + "\n")
    print(json.dumps({k: rec.get(k) for k in ("bench", "exact", "cycles", "token")}))
    return 0 if rec.get("exact") else 1


def run(cmd, work, name, env=None, cwd=None):
    t0 = time.monotonic()
    with open(work / f"{name}.log", "w") as log:
        p = subprocess.run(list(map(str, cmd)), cwd=cwd or ROOT, stdout=log, stderr=subprocess.STDOUT, env=env)
    return p.returncode, round(time.monotonic() - t0, 1)


# -- Qwen ROM plain-AR STREAM4 at P8191 (tools/exactness/qwen_rom_fulltoken.py) ------------------------
def qwen_rom(work, mode):
    build = work.parent / "qwen_rom_build"
    import fcntl
    lock = open(work.parent / "qwen_rom_build.lock", "a")
    fcntl.flock(lock, fcntl.LOCK_EX)          # L0 (fast) and full (nightly) share one build per commit
    if not (build / "build.json").exists():
        rc, sec = run([PY, TOOLS / "exactness/qwen_rom_fulltoken.py", "build", "--build", build, "--jobs", 16],
                      work, "build")
        if rc:
            return save(work, dict(bench=f"qwen_rom_{mode}", exact=False, cycles=None, error="build failed",
                                   log=str(work / "build.log")))
    rc, sec = run([PY, TOOLS / "exactness/qwen_rom_fulltoken.py", "run", "--build", build, "--work", work / "rt",
                   "--stages", mode, "--threads", 16], work, "run")
    r = json.loads((work / "rt/result.json").read_text()) if (work / "rt/result.json").exists() else {}
    r.update(bench=f"qwen_rom_{mode}", token=r.get("next_token"))
    if mode == "L0":
        r["cycles"] = r.get("stage_cycles", {}).get("L0")
    r.setdefault("exact", False)
    return save(work, r)


# -- HBM accelerator, Qwen3-8B TP2 at P8191 (tools/qwen_hbmacc_rt_token_w12.py) ---------------------------
HBMQ = S / "claude/qwen-hbmacc-8k"


def hbm_qwen(work, which):
    fix = {"L0": (HBMQ / "runs/a_p8191/L0", 160, "gold/tp2_l3/P8191", 5000, True, 4),
           "head": (HBMQ / "runs/a_p8191_w224_head/head", 224, "gold/tp2/P8191", 0, False, 16)}[which]
    src, winw, oracle, preroll, kv, _ = fix
    build = work.parent / f"hbm_qwen_build_w{winw}"
    cmd = [PY, TOOLS / "qwen_hbmacc_rt_token_w12.py", "--workdir", work / "rt", "--build-dir", build,
           "--stages", src / "stages.txt", "--layout", "/home/ubuntu/w12/img6144/L0-d0/layer0_rom.json",
           "--oracle-dir", HBMQ / oracle, "--preload", src / "preload.hex", "--pos", 8191, "--token", 24,
           "--preroll", preroll, "--threads", 4, "--winw", winw]
    if kv:
        cmd += ["--kv-dir", HBMQ / oracle / "kv_pre"]
    rc, sec = run(cmd, work, "driver")
    p = work / "rt/token_result.json"
    t = json.loads(p.read_text()) if p.exists() else {}
    stages = t.get("stages", {})
    rec = dict(bench=f"hbm_qwen_{which}", exact=bool(rc == 0 and t.get("status") == "pass"),
               cycles=t.get("total_cycles"), returncode=rc, wall_seconds=sec,
               stage_cycles={k: v.get("cycles") for k, v in stages.items()},
               token=t.get("rtl_token"), oracle_token=t.get("oracle_token"), logit_bits=t.get("rtl_logit_bits"),
               layer_x_checks=t.get("layer_x_checks"))
    if which == "head":
        rec["exact"] = rec["exact"] and t.get("rtl_token") == t.get("oracle_token")
    return save(work, rec)


# -- HBM accelerator, DeepSeek SM PQ/XMAP production gate on retained P1/P6 fixtures -----------------------
JOINT = S2 / "jobs/rawls-hbm-pq-xmap-joint-20261005-r2/fixtures"


def hbm_ds_joint(work):
    results, ok = {}, True
    total = 0
    for name, negative in [("stress", False), ("ar_l20", False), ("wg", False), ("other", False),
                           ("p6_stress", False), ("p6_l20", False), ("p6_wg", False), ("p6_other", False),
                           ("stress", True)]:
        key = name + ("_negative_fp4" if negative else "")
        active = 6 if name.startswith("p6_") else 1
        argv = [PY, TOOLS / "hbm_opt_integrated_20261005_joint.py", "run", "--production-dir",
                ROOT / "rtl/hbm_accel/sm/pq_production_20261005", "--work", work / "w", "--xmap", 1,
                "--active", active, "--jobs", 16, "--fixture", JOINT / f"{name}_haz1_g0"]
        if negative:
            argv.append("--negative-fp4")
        rc, sec = run(argv, work, key)
        rec = work / "w" / ("negative" if negative else "pq") / f"a{active}" / f"{name}_haz1_g0" / "result.json"
        m = json.loads(rec.read_text()) if rec.exists() else {}
        results[key] = dict(exit=rc, exact=m.get("exact"), accepted=m.get("accepted"), cycles=m.get("total_cycles"))
        ok &= rc == 0 and bool(m.get("accepted"))
        if key == "ar_l20":
            total = m.get("total_cycles")
    return save(work, dict(bench="hbm_ds_joint_p1", exact=bool(ok), cycles=total, runs=results))


# -- reduced-vehicle hardwired decode cores and the DSpark MTP golden/ISA ------------------------------------
def v41_hdc(work):
    out = work / "campaign.json"
    rc, sec = run([HPY, TOOLS / "rtl_hdc_v41_decode_campaign.py", "--output", out], work, "campaign",
                  env=dict(os.environ, OT_SCRATCH=str(work)))
    d = json.loads(out.read_text()) if out.exists() else {}
    e, s = d.get("end_to_end", {}), d.get("single_step", {})
    return save(work, dict(bench="v41_reduced_hdc", exact=bool(rc == 0 and d.get("status") == "pass"),
                           cycles=s.get("cycles"), token=s.get("next_token"), e2e_cycles=e.get("total_cycles"),
                           generated=e.get("generated_tokens"), returncode=rc, wall_seconds=sec))


def qwen_hdc(work):
    out = work / "campaign.json"
    rc, sec = run([HPY, TOOLS / "rtl_hdc_decode_campaign.py", "--output", out], work, "campaign")
    d = json.loads(out.read_text()) if out.exists() else {}
    e, s = d.get("end_to_end", {}), d.get("single_step", {})
    return save(work, dict(bench="qwen_reduced_hdc", exact=bool(rc == 0 and d.get("status") == "pass"),
                           cycles=s.get("cycles"), token=s.get("next_token"), e2e_cycles=e.get("total_cycles"),
                           generated=e.get("generated_tokens"), returncode=rc, wall_seconds=sec))


def v41_mtp(work):
    out = work / "mtp.json"
    rc, sec = run([HPY, TOOLS / "exactness/v41_mtp_isa.py", "--output", out], work, "mtp")
    d = json.loads(out.read_text()) if out.exists() else {}
    return save(work, dict(bench="v41_mtp_isa", exact=bool(rc == 0 and d.get("exact")), cycles=None,
                           token=(d.get("golden") or {}).get("greedy_tokens"), runs=d.get("runs"),
                           golden=d.get("golden"), returncode=rc, wall_seconds=sec))


BENCHES = {
    "qwen_rom_L0": lambda w: qwen_rom(w, "L0"),
    "qwen_rom_full": lambda w: qwen_rom(w, "full"),
    "hbm_qwen_L0": lambda w: hbm_qwen(w, "L0"),
    "hbm_qwen_head": lambda w: hbm_qwen(w, "head"),
    "hbm_ds_joint_p1": hbm_ds_joint,
    "v41_reduced_hdc": v41_hdc,
    "qwen_reduced_hdc": qwen_hdc,
    "v41_mtp_isa": v41_mtp,
}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("bench", choices=sorted(BENCHES))
    ap.add_argument("--work", type=Path, required=True)
    a = ap.parse_args()
    work = a.work.resolve()
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    t0 = time.monotonic()
    try:
        rc = BENCHES[a.bench](work)
    except Exception as exc:  # a harness failure is a FAIL row, never a silent skip
        rc = save(work, dict(bench=a.bench, exact=False, cycles=None, error=repr(exc)))
    r = json.loads((work / "result.json").read_text())
    r["bench_wall_seconds"] = round(time.monotonic() - t0, 1)
    (work / "result.json").write_text(json.dumps(r, indent=1, default=str) + "\n")
    sys.exit(rc)


if __name__ == "__main__":
    main()
