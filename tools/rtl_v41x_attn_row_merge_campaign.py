#!/usr/bin/env python3
"""Source-pinned exact packed window/selected-CKV attention-row merge gate."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/rtl/v41x_attn_row_merge.json"
RTL = ROOT / "rtl/chip/ot_chip_v41x_attn_row_merge.sv"
TB = ROOT / "rtl/test/tb_chip_v41x_attn_row_merge.sv"
VERILATOR = Path.home() / ".local/opentallas-tools/verilator-5.050/bin/verilator"
RE = re.compile(r"V41X_PACKED_MERGE PASS checked=(\d+) full_beats=(\d+) partial_beats=(\d+) "
                r"remote=(\d+) tag_fault=(\d+) range_fault=(\d+) batch=(\d+) batch_tag_fault=(\d+) batch_scalar=(\d+)")


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--scratch", type=Path, default=Path("/tmp/v41x_attn_row_merge_gate"))
    ap.add_argument("--output", type=Path, default=OUT)
    args = ap.parse_args()
    args.scratch.mkdir(parents=True, exist_ok=True)
    cmd = [str(VERILATOR), "--binary", "--timing", "-j", "4", "-Wno-fatal", "-Wno-WIDTH",
           "--top-module", "tb_chip_v41x_attn_row_merge", "-Mdir", str(args.scratch), str(RTL), str(TB)]
    build = subprocess.run(cmd, text=True, capture_output=True, check=False)
    exe = args.scratch / "Vtb_chip_v41x_attn_row_merge"
    run = subprocess.run([str(exe)], text=True, capture_output=True, check=False) if build.returncode == 0 else None
    match = RE.search(run.stdout) if run is not None else None
    counts = list(map(int, match.groups())) if match else None
    rec = {
        "schema": "v41x_attn_row_merge/1",
        "scope": "standalone ordered packed-row bridge with tagged four-bank and scalar banked WINDOW reads; synthetic full-format rows, no HBM timing or full token",
        "status": "pass" if build.returncode == 0 and run is not None and run.returncode == 0
                and counts == [14, 3, 1, 1, 1, 1, 1, 1, 1] else "fail",
        "checked_rows": counts[0] if counts else 0,
        "full_beats": counts[1] if counts else 0,
        "partial_beats": counts[2] if counts else 0,
        "remote_rows": counts[3] if counts else 0,
        "tag_faults_checked": counts[4] if counts else 0,
        "range_faults_checked": counts[5] if counts else 0,
        "four_bank_batches": counts[6] if counts else 0,
        "four_bank_tag_faults_checked": counts[7] if counts else 0,
        "banked_scalar_rows_checked": counts[8] if counts else 0,
        "backpressure": "first full beat held for three clocks and compared while kv_ready=0",
        "verilator": subprocess.run([str(VERILATOR), "--version"], text=True, capture_output=True).stdout.strip(),
        "sources": {str(p.relative_to(ROOT)): sha(p) for p in (RTL, TB, Path(__file__).resolve())},
        "build_rc": build.returncode,
        "sim_rc": run.returncode if run else None,
        "log_tail": (run.stdout if run else build.stderr)[-1000:],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(rec, indent=2, sort_keys=True) + "\n")
    print(f"attention row merge {rec['status']}: {args.output}")
    if rec["status"] != "pass":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
