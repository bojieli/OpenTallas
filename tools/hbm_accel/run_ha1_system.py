#!/usr/bin/env python3
"""HA1 (R1b) in system context: the reduced HBM system top (rtl/gpu_sys/ot_gpu_hbm_system.sv, 2 dies x 2 SIMT SMs)
running the real Qwen3 / DeepSeek-V4.1 decode programs, with the die's grid-barrier node replaced by per-SM tx-count
arrival counters (rtl/hbm_accel/txcount/ot_hbm_txcount_arrival.sv, no release broadcast).

The runner compiles rtl/hbm_accel/txcount/ot_hbm_txcount_node_shim.sv in place of rtl/gpu/ot_gpu_barrier_node.sv
(every pinned file byte-identical); --mode base keeps the original node logic (line-for-line copy) with the same
per-barrier monitor, --mode txcount defines HA1_TXCOUNT.  Every decode step is checked against the golden by the
system bench exactly as tools/gpu_sys/run_system.py does; the record adds the per-barrier boundary/wait totals.

    python3 tools/hbm_accel/run_ha1_system.py --model qwen --mode txcount --work DIR --out rec.json [--prepared]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "tools/gpu_sys"))
import run_system as rs  # noqa: E402

SHIM = ["rtl/hbm_accel/txcount/ot_hbm_txcount_arrival.sv", "rtl/hbm_accel/txcount/ot_hbm_txcount_node_shim.sv"]


def sources():
    dep = [s for s in rs.DEP_SRC if s != "rtl/gpu/ot_gpu_barrier_node.sv"]
    assert len(dep) == len(rs.DEP_SRC) - 1
    return rs.SYS_SRC + dep + SHIM + [rs.TB]


def build(work, model, mode):
    obj = Path(work) / f"obj_ha1_{mode}_{model}"
    exe = obj / "Vtb_gpu_hbm_system"
    if exe.exists():
        return exe
    cmd = [str(rs.VERILATOR), "--binary", "--timing", "-O2", "-j", os.environ.get("GPU_SYS_JOBS", "4"), "-Wno-fatal",
           "-Wno-lint", "-Wno-style", "-Wno-WIDTH", "--x-assign", "0", "--x-initial", "0",
           "--top-module", "tb_gpu_hbm_system", "--Mdir", str(obj)] + \
          [f"-G{k}={v}" for k, v in rs.MODEL_PARAMS[model].items()] + \
          (["-DHA1_TXCOUNT"] if mode == "txcount" else []) + [str(ROOT / s) for s in sources()]
    t0 = time.time()
    subprocess.run(cmd, check=True, cwd=ROOT, stdout=subprocess.DEVNULL)
    print(f"build {time.time() - t0:.0f} s", flush=True)
    return exe


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="qwen", choices=["qwen", "v41"])
    ap.add_argument("--mode", default="txcount", choices=["base", "txcount"])
    ap.add_argument("--work", required=True)
    ap.add_argument("--ngen", type=int, default=3)
    ap.add_argument("--nprompt", type=int, default=None)
    ap.add_argument("--prepared", action="store_true")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    work = Path(a.work)
    work.mkdir(parents=True, exist_ok=True)
    case = work / "case"
    if a.prepared:
        meta = json.loads((case / "expected.json").read_text())
    else:
        meta = rs.prepare(a.model, case, a.ngen, a.nprompt)
    exe = build(work, a.model, a.mode)
    log = work / f"sim_{a.mode}.log"
    t0 = time.time()
    with log.open("w") as f:
        r = subprocess.run([str(exe), "+DIR=."], cwd=case, stdout=f, stderr=subprocess.STDOUT)
    wall = time.time() - t0
    text = log.read_text()
    steps = [dict(zip(("step", "pos", "input", "next"), map(int, m.groups()[:4])), status=m.group(5),
                  step_cycles=int(m.group(6)) if m.group(6) else None)
             for m in re.finditer(r"STEP (\d+) pos (\d+) in (\d+) next (\d+) (OK|MISMATCH)?(?:\s+\(step (\d+))?", text)]
    final = re.search(r"TB_GPU_HBM_SYSTEM (PASS|FAIL) steps=(\d+) cq_tokens=(\d+) clk_sm_cycles=(\d+) fails=(\d+)", text)
    bars = [dict(inst=m.group(1), barriers=int(m.group(2)), boundary_sum=int(m.group(3)), boundary_max=int(m.group(4)),
                 wait_sum=int(m.group(5)))
            for m in re.finditer(r"HA1_BAR inst=(\S+) barriers=(\d+) boundary_sum=(\d+) boundary_max=(\d+) wait_sum=(\d+)", text)]
    ok = bool(final and final.group(1) == "PASS" and r.returncode == 0)
    rec = dict(schema="opentallas.hbm_accel.ha1_system.v1", model=a.model, mode=a.mode,
               tool="tools/hbm_accel/run_ha1_system.py", status="pass" if ok else "fail",
               golden=meta.get("golden"), expected_steps=meta["steps"], steps=steps,
               clk_sm_cycles=int(final.group(4)) if final else None, fails=int(final.group(5)) if final else None,
               barrier_monitor=bars, wall_seconds=round(wall, 1),
               simulator=subprocess.run([str(rs.VERILATOR), "--version"], capture_output=True, text=True).stdout.strip(),
               source_sha256={p: rs.sha(p) for p in sources() + ["tools/hbm_accel/run_ha1_system.py"]})
    Path(a.out).write_text(json.dumps(rec, indent=1) + "\n")
    print(text[-2500:])
    print("RUN_HA1_SYSTEM", "PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
