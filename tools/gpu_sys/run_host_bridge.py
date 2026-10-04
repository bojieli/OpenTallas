#!/usr/bin/env python3
"""Build and run rtl/test/gpu_sys/tb_gpu_host_bridge.sv: the host path of the GPU-organised HBM comparator system
(ot_host_if MODE 0 -> ot_gpu_host_bridge -> 2 x ot_gpu_cmdproc -> behavioural SM stubs, resets from
ot_gpu_reset_ctrl), driven by a bench host speaking runtime/hdc/driver.py's protocol.

    python3 tools/gpu_sys/run_host_bridge.py [--sims icarus,verilator] [--seeds 1,2,3]
                                             [--out results/rtl/hbm_system_rtl_20261003/host_bridge.json]

Every (simulator, seed) run must print PASS for every check and TB_GPU_HOST_BRIDGE PASS.  Latencies are the
bench's measurements in ps: the clk_host edge that samples eng_start to the clk_sm edge that samples the first
launch_v (any die), and the clk_sm edge that samples the step's last sm_done to the clk_host edge that samples
eng_done (normal steps only).  Exits nonzero on any FAIL.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
VERILATOR = Path(os.environ.get("OPENTALLAS_TOOL_ROOT", Path.home() / ".local/opentallas-tools")) / \
    "verilator-5.050/bin/verilator"
BENCH = "rtl/test/gpu_sys/tb_gpu_host_bridge.sv"
RTL = ["rtl/host/ot_host_if.sv", "rtl/gpu_sys/ot_gpu_host_bridge.sv", "rtl/gpu_sys/ot_gpu_cmdproc.sv",
       "rtl/gpu_sys/ot_gpu_reset_ctrl.sv", "rtl/gpu_sys/ot_gpu_cdc_fifo.sv", "rtl/link/ot_link_afifo.sv"]
REFS = ["rtl/gpu_sys/ot_gpu_hbm_system.sv", "runtime/hdc/driver.py"]      # parameters / protocol mirrored
DEFAULT_OUT = ROOT / "results/rtl/hbm_system_rtl_20261003/host_bridge.json"
SCHEMA = "opentallas.gpu_sys.host_bridge.v1"
CHECKS = ["reset_order", "loader_delivery", "cq_request1", "sm_fault", "result_mismatch", "doorbell_tokpos",
          "stream_order", "step_results", "cdc_fault_zero", "axi_dma", "enable0_outputs_zero"]
CHECK_DESC = {
    "reset_order": "ot_gpu_reset_ctrl from one por_n: mem and link released before sm, sm before host",
    "loader_delivery": "4 commands per die and 100 instruction words per SM arrive on cmd_we/im_we exactly once, "
                       "with the right die/SM select, address and data, and nothing else is written",
    "cq_request1": "GENERATE (plen 5, max_new 3, greedy|stop-at-EOS, EOS not hit): CQ entries pos 4,5,6, tokens "
                   "f(token,pos) of the last prompt step and the next two, kind 1,1,2, status 0,0,length, tag, slot, "
                   "generated 1,2,3, phase 1; no fourth entry; 7 steps; SQ_HEAD advanced",
    "sm_fault": "die 1 SM 1 raises sm_fault -> cmdproc status 1 -> eng_fault -> one CQ entry kind 2 (last) status 7 "
                "engine_fault (token = die 0's), STATUS.engine_fault set",
    "result_mismatch": "die 1 posts a different RESULT -> eng_fault -> one CQ entry kind 2 status 7 engine_fault",
    "doorbell_tokpos": "every eng_start carries the step's token/pos (prompt teacher-forced, then the fed-back "
                       "generated token); each die's doorbell and each launch carry exactly that step",
    "stream_order": "per die: launches in graph order with the loaded mask/PC; no LAUNCH while an SM of the "
                    "previous kernel has not signalled done",
    "step_results": "every normal eng_done returns f(token,pos) without eng_fault; fault requests raise eng_fault",
    "cdc_fault_zero": "the bridge's CDC overflow fault stays 0",
    "axi_dma": "the host_if DMA presents AW and W together (the bench memory's assumption)",
    "enable0_outputs_zero": "ENABLE=0 ot_gpu_host_bridge and ot_gpu_cmdproc drive every output 0 (=== 0, no X)",
}


def sha(rel: str) -> str:
    return hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()


def build(sim: str, bdir: Path) -> list[str]:
    srcs = [str(ROOT / s) for s in [BENCH, *RTL]]
    if sim == "icarus":
        exe = bdir / "tb.vvp"
        r = subprocess.run(["iverilog", "-g2012", "-o", str(exe), *srcs], capture_output=True, text=True)
        (bdir / "build_icarus.log").write_text(r.stdout + r.stderr)
        if r.returncode:
            raise SystemExit(f"iverilog failed, see {bdir / 'build_icarus.log'}")
        return ["vvp", "-n", str(exe)]
    obj = bdir / "vobj"
    r = subprocess.run([str(VERILATOR), "--binary", "--timing", "-j", "8", "-Wno-fatal", "-Wno-WIDTH",
                        "-Wno-MULTIDRIVEN", "--top-module", "tb_gpu_host_bridge", "-Mdir", str(obj), *srcs],
                       capture_output=True, text=True, cwd=bdir)
    (bdir / "build_verilator.log").write_text(r.stdout + r.stderr)
    if r.returncode:
        raise SystemExit(f"verilator failed, see {bdir / 'build_verilator.log'}")
    return [str(obj / "Vtb_gpu_host_bridge")]


def parse(log: str) -> dict:
    checks = {}
    for ln in log.splitlines():
        m = re.match(r"(PASS|FAIL) (\w+)", ln)
        if m and m[2] in CHECKS:
            checks[m[2]] = checks.get(m[2], True) and m[1] == "PASS"
    lat = {}
    for m in re.finditer(r"LAT (\w+)_ps n=(\d+)(?: min=([\d.]+) max=([\d.]+))? mean=([\d.]+)", log):
        lat[m[1]] = {"n": int(m[2]), "mean_ps": float(m[5]),
                     **({"min_ps": float(m[3]), "max_ps": float(m[4])} if m[3] else {})}
    cqe = [ln for ln in log.splitlines() if ln.startswith("CQE ")]
    return {"checks": checks, "latency": lat, "cq_entries": cqe,
            "bench_pass": "TB_GPU_HOST_BRIDGE PASS" in log,
            "fail_lines": [ln for ln in log.splitlines() if ln.startswith("FAIL")]}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--sims", default="icarus,verilator")
    ap.add_argument("--seeds", default="1,2,3")
    ap.add_argument("--build-dir", type=Path, default=None)
    a = ap.parse_args()
    bdir = a.build_dir or Path(tempfile.mkdtemp(prefix="gpu_host_bridge_"))
    bdir.mkdir(parents=True, exist_ok=True)
    runs, fails = [], []
    sims = {}
    for sim in [s for s in a.sims.split(",") if s]:
        cmd = build(sim, bdir)
        ver = (subprocess.run(["iverilog", "-V"], capture_output=True, text=True).stdout.splitlines() or [""])[0] \
            if sim == "icarus" else subprocess.run([str(VERILATOR), "--version"], capture_output=True,
                                                   text=True).stdout.strip()
        sims[sim] = {"version": ver, "flags": "-g2012" if sim == "icarus" else
                     "--binary --timing -j 8 -Wno-fatal -Wno-WIDTH -Wno-MULTIDRIVEN"}
        for seed in [int(s) for s in a.seeds.split(",") if s]:
            r = subprocess.run([*cmd, f"+SEED={seed}"], capture_output=True, text=True, cwd=bdir)
            log = r.stdout + r.stderr
            (bdir / f"sim_{sim}_{seed}.log").write_text(log)
            p = parse(log)
            missing = [c for c in CHECKS if c not in p["checks"]]
            ok = p["bench_pass"] and not missing and all(p["checks"].values())
            runs.append({"simulator": sim, "seed": seed, "pass": ok, **p, "missing_checks": missing})
            print(f"{'PASS' if ok else 'FAIL'} {sim} seed={seed} " +
                  " ".join(f"{k}={'PASS' if v else 'FAIL'}" for k, v in p["checks"].items()))
            if not ok:
                fails.append(f"{sim} seed {seed}: {p['fail_lines'][:5] or missing or 'no PASS banner'}")
    checks = {c: {"description": CHECK_DESC[c],
                  "pass": bool(runs) and all(r["checks"].get(c, False) for r in runs)} for c in CHECKS}
    lat_all = {}
    for key in ("eng_start_to_first_launch", "last_done_to_eng_done", "eng_start_to_eng_done"):
        vals = [r["latency"][key] for r in runs if key in r["latency"]]
        if vals:
            lat_all[key] = {"runs": len(vals), "mean_ps": sum(v["mean_ps"] for v in vals) / len(vals),
                            **({"min_ps": min(v["min_ps"] for v in vals), "max_ps": max(v["max_ps"] for v in vals)}
                               if "min_ps" in vals[0] else {})}
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    rec = {
        "schema": SCHEMA,
        "verdict": "PASS" if not fails and runs else "FAIL",
        "failures": fails,
        "git_head": head,
        "note_worktree": "sources are pinned by sha256 below; the worktree may carry uncommitted files",
        "simulator": sims,
        "sources": {s: sha(s) for s in [BENCH, *RTL, *REFS, "tools/gpu_sys/run_host_bridge.py"]},
        "configuration": {
            "ot_host_if": "NSLOT 16, MODE 0, ENG_CTX 16, NW 16, PLB 8, CTX_MAX 64, AW 24, KVW 1024 "
                          "(as instantiated in ot_gpu_hbm_system.sv)",
            "ot_gpu_host_bridge": "ENABLE 1, ND 2, NSM 2, CB 8, IMW 13",
            "ot_gpu_cmdproc": "2 x ENABLE 1, NSM 2, NCMD 256",
            "ot_gpu_reset_ctrl": "ENABLE 1 (SYNC 2, HOLD 4), one por_n",
            "clocks_ps": {"clk_host": 4000, "clk_sm": 833, "clk_mem": 1000, "clk_link": 900},
            "host": "SQ 0x0000 LOG2 6, CQ 0x1000 LOG2 8, prompts 0x10000 + slot*0x400, MSI 0xF000; "
                    "driver.py init sequence; CQ polled by phase bit, returned through CQ_HEAD",
            "graph": "per die: LAUNCH mask 01 pc 0x104+0x10d, LAUNCH mask 10 pc 0x204+0x10d, LAUNCH mask 11 "
                     "pc 0x304+0x10d, END",
            "sm_stub": "done 10..300 clk_sm cycles after launch; SM 0 posts RESULT (token*7+pos)&0xFFFF 1..4 "
                       "cycles before its done on the last kernel",
            "requests": ["slot 0 tag 0x1234 prompt [11,22,333,4444,5555] max_new 3 EOS {0xFFFE,0xFFFD}",
                         "slot 1 tag 0x2345: die 1 SM 1 sm_fault on kernel 1 of the first step",
                         "slot 2 tag 0x3456: die 1 RESULT ^ 1 on the first step"],
        },
        "checks": checks,
        "latency_ps": lat_all,
        "latency_definition": {
            "eng_start_to_first_launch": "clk_host edge sampling eng_start -> clk_sm edge sampling the first "
                                         "launch_v of the step (either die)",
            "last_done_to_eng_done": "clk_sm edge sampling the step's last sm_done (either die) -> clk_host edge "
                                     "sampling eng_done",
            "eng_start_to_eng_done": "whole step including the stubs' random kernel durations (not a hardware "
                                     "figure)",
        },
        "runs": runs,
        "observations": [
            "An engine fault is posted by ot_host_if as kind 2 (last) with status 7 engine_fault; kind 3 (error) is "
            "reserved for descriptor errors. The bench checks that encoding.",
            "ot_gpu_cmdproc aborts the list on sm_fault but leaves the die's other SMs running; their later "
            "sm_done/res_v are ignored only while the processor is idle. The bench clears its SM stubs after the "
            "fault (an SM reset is outside these modules).",
        ],
    }
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(rec, indent=1) + "\n")
    for f in fails:
        print("FAIL", f)
    print(f"RUN_HOST_BRIDGE {rec['verdict']} -> {a.out}")
    return 0 if rec["verdict"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
