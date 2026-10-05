#!/usr/bin/env python3
"""Cycle-equivalence gate for the V4.1 attention group-column physical cut.

Builds tb_v41_attn_neighborhood_equiv with Verilator 5.050 for the SRAM-macro
mapping (macro behavioural models) and the behavioural column, runs every
seed, optionally runs a short 4-state Icarus pass of the macro mapping, and
writes a source-pinned record.

    python3 tools/rtl_v41_attn_neighborhood_equiv.py \
        --output results/rtl/v41_attn_neighborhood_equiv.json
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

ROOT = Path(__file__).resolve().parents[1]
VERILATOR = Path(os.environ.get("OT_VERILATOR",
                                str(Path.home() / ".local/opentallas-tools/verilator-5.050/bin/verilator")))
M = "physical/asap7_memory_macros"
SOURCES = [
    "rtl/test/tb_v41_attn_neighborhood_equiv.sv",
    "rtl/chip/physical/ot_v41_attn_neighborhood.sv",
    "rtl/chip/physical/ot_v41_attn_stage_ctl.sv",
    "rtl/chip/physical/ot_v41_attn_col_slice.sv",
    "rtl/chip/ot_chip_v41x_window_stage4.sv",
    "rtl/hdc/v41x/ot_hdc_v41x_attn_staging.sv",
    f"{M}/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v",
    f"{M}/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v",
    f"{M}/ot_sram_1r1w_512x128_m4_r2c2/ot_sram_1r1w_512x128_m4_r2c2.v",
]
PASS_RE = re.compile(r"V41_ATTN_NEIGHBORHOOD_EQUIV (PASS|FAIL) (.*)")


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def parse(out: str) -> dict:
    m = PASS_RE.search(out)
    if not m:
        return {"pass": False, "stdout_tail": out[-2000:]}
    fields = dict(kv.split("=") for kv in m.group(2).split())
    return {"pass": m.group(1) == "PASS", **{k: int(v) for k, v in fields.items()}}


def run_verilator(tmp: Path, sram: int, seed: int, cycles: int) -> dict:
    mdir = tmp / f"v_{sram}_{seed}"
    build = [str(VERILATOR), "--binary", "--timing", "-j", "8", "-Wno-fatal", "-Wno-lint", "-Wno-style",
             "--top-module", "tb_v41_attn_neighborhood_equiv", f"-GSRAM_MACRO={sram}",
             f"-GCYCLES={cycles}", f"-GSEED={seed}", "--Mdir", str(mdir), "-o", "veq",
             *[str(ROOT / s) for s in SOURCES]]
    b = subprocess.run(build, capture_output=True, text=True, cwd=ROOT)
    if b.returncode:
        return {"pass": False, "build_returncode": b.returncode, "stderr_tail": b.stderr[-2000:]}
    r = subprocess.run([str(mdir / "veq")], capture_output=True, text=True, timeout=7200)
    return {"simulator": "verilator", "sram_macro": sram, "seed": seed, "returncode": r.returncode,
            **parse(r.stdout)}


def run_icarus(tmp: Path, cycles: int) -> dict:
    vvp = tmp / "eq.vvp"
    b = subprocess.run(["iverilog", "-g2012", "-P", "tb_v41_attn_neighborhood_equiv.SRAM_MACRO=1",
                        "-P", f"tb_v41_attn_neighborhood_equiv.CYCLES={cycles}", "-o", str(vvp),
                        *SOURCES], capture_output=True, text=True, cwd=ROOT)
    if b.returncode:
        return {"pass": False, "build_returncode": b.returncode, "stderr_tail": b.stderr[-2000:]}
    r = subprocess.run(["vvp", "-n", str(vvp)], capture_output=True, text=True, timeout=14400)
    return {"simulator": "icarus (4-state)", "sram_macro": 1, "seed": 1, "returncode": r.returncode,
            **parse(r.stdout)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", required=True)
    ap.add_argument("--cycles", type=int, default=200000)
    ap.add_argument("--seeds", default="1,2,3")
    ap.add_argument("--icarus-cycles", type=int, default=0)
    a = ap.parse_args()
    runs = []
    with tempfile.TemporaryDirectory(prefix="w2c_eq_") as t:
        tmp = Path(t)
        for seed in [int(s) for s in a.seeds.split(",")]:
            for sram in (1, 0):
                runs.append(run_verilator(tmp, sram, seed, a.cycles))
                print(json.dumps(runs[-1]), flush=True)
        if a.icarus_cycles:
            runs.append(run_icarus(tmp, a.icarus_cycles))
            print(json.dumps(runs[-1]), flush=True)
    ok = bool(runs) and all(r.get("pass") for r in runs)
    v = subprocess.run([str(VERILATOR), "--version"], capture_output=True, text=True).stdout.strip()
    rec = {
        "schema": "v41_attn_neighborhood_equiv/1",
        "pass": ok,
        "claim": ("cycle equivalence of the group-column cut (1 ot_v41_attn_stage_ctl + 16 "
                  "ot_v41_attn_col_slice) against ot_chip_v41x_window_stage4, the merge beat update "
                  "rules of ot_chip_v41x_attn_row_merge and behavioural ot_hdc_v41x_attn_staging, "
                  "every cycle on response metadata, the 16,896-bit rotation register, the "
                  "16,960-bit beat and the staging read data, under random fills/invalidations/"
                  "requests/beats/staging traffic"),
        "scope": ("physical-cut equivalence only; the merge FSM itself is not replaced (its beat "
                  "strobes are driven randomly), no numeric attention engine or token claim"),
        "runs": runs,
        "verilator_version": v,
        "sources_sha256": {s: sha(ROOT / s) for s in SOURCES},
        "generator": "tools/rtl_v41_attn_neighborhood_equiv.py",
        "generator_sha256": sha(Path(__file__)),
    }
    out = ROOT / a.output
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rec, indent=1, sort_keys=True) + "\n")
    print("PASS" if ok else "FAIL", out)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
