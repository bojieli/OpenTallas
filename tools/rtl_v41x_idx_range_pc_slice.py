#!/usr/bin/env python3
"""Equivalence gate for the physical one-PC V4.1 index range arbiter slice."""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCES = [ROOT / p for p in (
    "rtl/hdc/v41x/ot_hdc_v41x_idx_range_pc_arb.sv",
    "rtl/hdc/v41x/ot_hdc_v41x_idx_range_pc_slice.sv",
    "rtl/test/tb_hdc_v41x_idx_range_pc_slice.sv",
)]
OUT = ROOT / "results/rtl/hdc_v41x_idx_range_pc_slice.json"


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="v41-range-pc-slice-") as d:
        binary = Path(d) / "slice.vvp"
        subprocess.run(["iverilog", "-g2012", "-s", "tb_hdc_v41x_idx_range_pc_slice",
                        "-o", str(binary), *map(str, SOURCES)], check=True, cwd=ROOT)
        result = subprocess.run(["vvp", str(binary)], check=True, capture_output=True,
                                text=True, timeout=60, cwd=ROOT)
        m = re.search(r"V41X_RANGE_PC_SLICE_PASS cycles=(\d+)", result.stdout)
        assert m and int(m.group(1)) == 2000, result.stdout
    script = Path(__file__).resolve()
    record = {
        "schema": "opentallas.hdc-v41x-idx-range-pc-slice.v1",
        "status": "pass",
        "equivalence_cycles": 2000,
        "description": "One physical one-PC slice matches the source-pinned NPC=1 parent arbiter for randomized request grants, HBM context tags and shared response data; QUANTUM128.",
        "limitation": "Randomized local equivalence only. No four-stack token, full 32-PC route, or SRAM macro closure follows from this gate.",
        "tools": {
            "iverilog": subprocess.run(["iverilog", "-V"], capture_output=True,
                                      text=True, check=True).stdout.splitlines()[0],
            "vvp": subprocess.run(["vvp", "-V"], capture_output=True,
                                 text=True, check=True).stderr.splitlines()[0],
        },
        "input_sha256": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                         for p in [*SOURCES, script]},
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(record, indent=2) + "\n")
    print("PASS one-PC slice equivalence 2000 cycles")


if __name__ == "__main__":
    main()
