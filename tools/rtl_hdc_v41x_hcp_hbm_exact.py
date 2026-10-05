#!/usr/bin/env python3
"""Reduced real HCP projection with byte-identical ROM and banked HBM weights.

This is a weight-supply gate for one hyper-connection op. It does not price
contention with QE, ME, KV, index or the links, and is not a die/token rate.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import rtl_hdc_v41x_hcp_campaign as hc  # noqa: E402

SOURCES = [
    ROOT / "rtl/hdc/v41x/ot_hdc_v41x_hcp.sv",
    ROOT / "rtl/hdc/ot_hdc_fastfp.sv",
    ROOT / "rtl/hdc/v41/ot_hdc_fdiv.sv",
    ROOT / "rtl/hdc/ot_hdc_delay.sv",
    ROOT / "rtl/hdc/ot_hdc_sfu.sv",
    ROOT / "rtl/hdc/hbm/ot_hdc_v41x_weight_window.sv",
    ROOT / "rtl/hdc/hbm/ot_hdc_v41x_hcp_hbm_window.sv",
    ROOT / "rtl/test/tb_hdc_v41x_hcp_hbm_exact.sv",
    ROOT / "rtl/test/v41x_hcp_hbm_exact_harness.cpp",
]
PINS = SOURCES + [
    ROOT / "tools/hdc_golden.py", ROOT / "tools/hdc_golden_v41.py",
    ROOT / "tools/rtl_hdc_v41x_hcp_campaign.py", Path(__file__).resolve(),
]
PATTERN = re.compile(
    r"HCP_AB_PASS mode=(\d+) outputs=(\d+) errors=(\d+) faults=(\d+) "
    r"sectors=(\d+) wait=(\d+) run=(\d+)"
)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def checked(cmd: list[str], *, cwd: Path, timeout: int = 1200) -> str:
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    if p.returncode:
        raise RuntimeError(f"{cmd[0]} exited {p.returncode}:\n{p.stdout[-3000:]}\n{p.stderr[-3000:]}")
    return p.stdout


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scratch", type=Path, default=Path("/tmp/v41-hcp-hbm-gate"))
    ap.add_argument("--output", type=Path, default=ROOT / "results/rtl/hdc_v41x_hcp_hbm_exact.json")
    ap.add_argument("--verilator", default="verilator")
    ap.add_argument("--reuse-build", action="store_true")
    args = ap.parse_args()
    args.scratch.mkdir(parents=True, exist_ok=True)
    hc.G.set_arith("chunk8")
    cases, _ = hc.real_cases()
    selected = cases[0]
    fixture = hc.write_vectors(args.scratch, [selected], 8)
    assert selected["name"] == "reduced L24 hc_attn x6" and fixture == {
        "weight_words": 240, "x_words": 60, "results": 144
    }
    vectors = [args.scratch / f"hcp_{s}.mem" for s in ("meta", "cmd", "w", "x", "exp")]

    obj = args.scratch / "obj"
    exe = obj / "Vtb_hdc_v41x_hcp_hbm_exact"
    if not args.reuse_build or not exe.exists():
        checked([args.verilator, "--cc", "--exe", "--build", "-j", "2", "-O1", "-Wno-fatal",
                 "-Wno-WIDTH", "-Wno-UNUSED", "-Wno-TIMESCALEMOD", "--top-module",
                 "tb_hdc_v41x_hcp_hbm_exact", "-Mdir", str(obj),
                 *map(str, SOURCES)], cwd=ROOT)
    arms = {}
    for name, plus in (("rom", []), ("hbm", ["+HBM"])):
        log = checked([str(exe), *plus], cwd=args.scratch)
        m = PATTERN.search(log)
        if not m:
            raise RuntimeError(f"{name} has no PASS line:\n{log[-3000:]}")
        mode, outputs, errors, faults, sectors, wait, run = map(int, m.groups())
        if mode != int(name == "hbm") or outputs != 144 or errors or faults:
            raise RuntimeError(f"{name} failed exact result check: {m.group(0)}")
        if name == "hbm" and sectors != 8 * 240:
            raise RuntimeError(f"HBM fetched {sectors} sectors, expected 1920")
        arms[name] = {"outputs_exact": outputs, "mismatches": errors, "faults": faults,
                      "hbm_sectors": sectors, "weight_wait_cycles": wait,
                      "hcp_run_cycles": run, "log_sha256": hashlib.sha256(log.encode()).hexdigest()}
    if arms["rom"]["hcp_run_cycles"] != arms["hbm"]["hcp_run_cycles"]:
        raise RuntimeError("HCP execution changed after replacing only its weight source")
    record = {
        "schema": "opentallas.rtl.hdc_v41x_hcp_hbm_exact.v1", "status": "pass",
        "claim_boundary": "One real reduced L24 hyper-connection projection, six positions, eight HCP banks in HBM. Both arms use the same command, activations, checkpoint-derived FP32 weights and golden outputs. No full token, shared HBM contention, full-shape width, physical route or chip throughput claim.",
        "source_commit": checked(["git", "rev-parse", "HEAD"], cwd=ROOT).strip(),
        "source_sha256": {str(p.relative_to(ROOT)): digest(p) for p in PINS},
        "fixture_sha256": {p.name: digest(p) for p in vectors},
        "fixture": {"name": selected["name"], "positions": 6, "outputs_per_position": 24,
                    "K": 640, **fixture},
        "hbm_layout": {"sector_bytes": 32, "bank_count": 8, "window_words_per_bank": 256,
                       "resident_window_bytes": 8 * 256 * 32,
                       "fetched_weight_bytes": 8 * 240 * 32,
                       "layout": "bank-contiguous, then HCP word address, then eight little-lane FP32 values"},
        "arms": arms,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps({"arms": arms, "output": str(args.output)}))


if __name__ == "__main__":
    main()
