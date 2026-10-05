#!/usr/bin/env python3
"""Build and run tb_gpu_cdc_fifo (Verilator --binary --timing), compare with tools/gpu_sys/cdc_sizing.py, and
lint ot_gpu_cdc_fifo (verilator --lint-only -Wall, ENABLE=0 and 1).

The bench runs all five clock pairs x depths 4/8/16 concurrently in one simulation; the predicted AW per pair is
passed from the model with -G, so the bench's model check is the model's current output.

    python3 tools/gpu_sys/run_cdc_fifo.py [--out results/rtl/hbm_system_rtl_20261003/cdc_fifo.json]

Exits nonzero on any FAIL.  Lint: only UNUSED* warnings are tolerated (the ENABLE=0 branch leaves inputs unused
and the wrapper does not consume ot_link_afifo's wfreed/rcount); every other -Wall warning fails.
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
sys.path.insert(0, str(HERE))
import cdc_sizing as M  # noqa: E402

VERILATOR = Path.home() / ".local/opentallas-tools/verilator-5.050/bin/verilator"
RTL = [ROOT / "rtl/gpu_sys/ot_gpu_cdc_fifo.sv", ROOT / "rtl/link/ot_link_afifo.sv"]
BENCH = ROOT / "rtl/test/gpu_sys/tb_gpu_cdc_fifo.sv"
TOOLS = [HERE / "cdc_sizing.py", Path(__file__).resolve()]
DEFAULT_OUT = ROOT / "results/rtl/hbm_system_rtl_20261003/cdc_fifo.json"
SCHEMA = "opentallas.gpu_sys.cdc_fifo.v1"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def lint(enable: int) -> dict:
    cmd = [str(VERILATOR), "--lint-only", "-Wall", "--top-module", "ot_gpu_cdc_fifo", f"-GENABLE={enable}",
           *map(str, RTL)]
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    msgs = [ln for ln in (r.stdout + r.stderr).splitlines() if ln.startswith("%")]
    warns = [ln for ln in msgs if ln.startswith("%Warning-")]
    errors = [ln for ln in msgs if ln.startswith("%Error") and "Exiting due to" not in ln]
    waived = [ln for ln in warns if re.match(r"%Warning-UNUSED", ln)]
    bad = [ln for ln in warns if ln not in waived] + errors
    return {"enable": enable, "pass": not bad, "waived_unused": [w.split(": ", 1)[-1] for w in waived],
            "violations": bad}


def build(bdir: Path, preds: list[int]) -> Path:
    gparams = [f"-GPRED_AW_{i}={aw}" for i, aw in enumerate(preds)]
    cmd = [str(VERILATOR), "--binary", "--timing", "-j", "2", "-Wno-fatal", "-Wno-WIDTH",
           "--top-module", "tb_gpu_cdc_fifo", "-Mdir", str(bdir / "obj"), *gparams, str(BENCH), *map(str, RTL)]
    r = subprocess.run(cmd, cwd=bdir, capture_output=True, text=True,
                       env={**os.environ, "MAKEFLAGS": "-j2"})
    (bdir / "build.log").write_text(r.stdout + r.stderr)
    if r.returncode != 0:
        raise SystemExit(f"verilator build failed, see {bdir / 'build.log'}")
    return bdir / "obj" / "Vtb_gpu_cdc_fifo"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--build-dir", type=Path, default=None)
    a = ap.parse_args()

    model = M.table()
    preds = {(p["write_period_ps"], p["read_period_ps"]): p for p in model["bench_predictions"]}
    pred_aws = [preds[pair]["predicted_aw"] for pair in M.BENCH_PAIRS]
    if not all(2 <= aw <= 4 for aw in pred_aws):
        print(f"FAIL predicted AW outside the bench's 2..4: {pred_aws}")
        return 1
    model_errs = M.self_check()
    print(f"{'FAIL' if model_errs else 'PASS'} cdc_sizing self-check {model_errs or ''}")

    lints = [lint(0), lint(1)]
    for li in lints:
        print(f"{'PASS' if li['pass'] else 'FAIL'} lint -Wall ENABLE={li['enable']} "
              f"(waived UNUSED: {len(li['waived_unused'])}) {li['violations'] or ''}")

    bdir = a.build_dir or Path(tempfile.mkdtemp(prefix="gpu_cdc_fifo_"))
    bdir.mkdir(parents=True, exist_ok=True)
    exe = build(bdir, pred_aws)
    r = subprocess.run([str(exe)], cwd=bdir, capture_output=True, text=True)
    log = r.stdout + r.stderr
    (bdir / "sim.log").write_text(log)
    lines = [ln for ln in log.splitlines() if re.match(r"(PASS|FAIL|RATE|TB_GPU)", ln)]
    print("\n".join(ln for ln in lines if not ln.startswith("RATE")))

    rates, integ, thr, mod = {}, {}, {}, {}
    for ln in lines:
        if m := re.match(r"RATE pair=(\d+)/(\d+) depth=(\d+) rate=([\d.]+)", ln):
            rates[(int(m[1]), int(m[2]), int(m[3]))] = float(m[4])
        elif m := re.match(r"(PASS|FAIL) integrity pair=(\d+)/(\d+) depth=(\d+) entries=(\d+) full_stall_cycles=(\d+)",
                           ln):
            integ[(int(m[2]), int(m[3]), int(m[4]))] = {"pass": m[1] == "PASS", "entries": int(m[5]),
                                                       "full_stall_cycles": int(m[6])}
        elif m := re.match(r"(PASS|FAIL) throughput pair=(\d+)/(\d+)", ln):
            thr[(int(m[2]), int(m[3]))] = m[1] == "PASS"
        elif m := re.match(r"(PASS|FAIL) model pair=(\d+)/(\d+) predicted_depth=(\d+) smallest_measured_depth=(\d+)",
                           ln):
            mod[(int(m[2]), int(m[3]))] = (m[1] == "PASS", int(m[5]))
    ovf_ok = any(ln.startswith("PASS ovf_fault") for ln in lines)
    en0_ok = any(ln.startswith("PASS enable0") for ln in lines)
    tb_ok = "TB_GPU_CDC_FIFO PASS" in lines

    cases, fails = [], []
    for tw, tr in M.BENCH_PAIRS:
        p = preds[(tw, tr)]
        smallest = mod.get((tw, tr), (False, 0))[1]
        # Python-side re-check: predicted depth = smallest depth measuring >= 0.99, and the worst-phase model
        # rate is a lower bound on every measurement.
        meas_smallest = min((1 << aw for aw in M.BENCH_AWS if rates.get((tw, tr, 1 << aw), 0) >= M.RATE_PASS),
                            default=0)
        for aw in M.BENCH_AWS:
            d = 1 << aw
            rate = rates.get((tw, tr, d))
            worst = p["predicted_worst_rate"][str(d)]
            ig = integ.get((tw, tr, d), {"pass": False})
            bound_ok = rate is not None and rate >= worst - 1e-3
            cases.append({
                "write_period_ps": tw, "read_period_ps": tr, "depth": d, "aw": aw,
                "measured_entries_per_slow_cycle": rate,
                "model_mean_rate": p["predicted_mean_rate"][str(d)], "model_worst_rate": worst,
                "worst_rate_bound_holds": bound_ok, "integrity": ig,
                "is_predicted_depth": d == p["predicted_depth"],
                "pass": bool(ig["pass"] and bound_ok and (d != p["predicted_depth"] or (rate or 0) >= M.RATE_PASS)),
            })
            if not cases[-1]["pass"]:
                fails.append(f"case {tw}/{tr} depth {d}")
        if not (thr.get((tw, tr)) and mod.get((tw, tr), (False,))[0] and meas_smallest == p["predicted_depth"]
                and smallest == meas_smallest):
            fails.append(f"model/throughput {tw}/{tr}: predicted {p['predicted_depth']} measured {meas_smallest}")
    for name, ok in (("ovf_fault", ovf_ok), ("enable0", en0_ok), ("bench", tb_ok), ("sizing self-check",
                                                                                    not model_errs)):
        if not ok:
            fails.append(name)
    fails += [f"lint ENABLE={li['enable']}" for li in lints if not li["pass"]]

    ver = subprocess.run([str(VERILATOR), "--version"], capture_output=True, text=True).stdout.strip()
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    rec = {
        "schema": SCHEMA,
        "verdict": "PASS" if not fails else "FAIL",
        "failures": fails,
        "git_head": head,
        "simulator": {"name": "verilator", "version": ver, "flags": "--binary --timing -j 2"},
        "sources": {str(p.relative_to(ROOT)): sha(p) for p in [*RTL, BENCH, *TOOLS]},
        "sync": M.SYNC_DEFAULT, "rate_pass_threshold": M.RATE_PASS,
        "bench": {"entries_per_integrity_fifo": 20000, "throughput_window_slow_cycles": 20000,
                  "pass_lines": [ln for ln in lines if not ln.startswith("RATE")]},
        "predictions": model["bench_predictions"],
        "cases": cases,
        "checks": {"ovf_fault_stays_0": ovf_ok, "enable0_outputs_zero": en0_ok, "bench_pass": tb_ok},
        "lint": lints,
        "boundaries": model["boundaries"],
        "full_shape_ingress": model["full_shape_ingress"],
        "note": ("Depth model: D >= (SYNC+1)(Tw+Tr)/T_slow (worst phase), 2^AW, AW>=2. The mean-phase rate estimate "
                 "(SYNC+1/2)(Tw+Tr) is optimistic for undersized FIFOs (depth 4 measures ~0.80 vs 0.83-0.87 "
                 "estimated); the worst-phase rate is a lower bound on every measurement and the predicted depth "
                 "is the smallest measured depth reaching 0.99."),
    }
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(rec, indent=1) + "\n")
    for f in fails:
        print("FAIL", f)
    print(f"RUN_CDC_FIFO {rec['verdict']} -> {a.out}")
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main())
