#!/usr/bin/env python3
"""Exact shipped-group attention position-round gate and source record."""
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path

import hdc_isa as I
import hdc_timing as T

ROOT = Path(__file__).resolve().parents[1]
SOURCES = [ROOT / p for p in (
    "rtl/hdc/ot_hdc_dyn_ttiles.sv",
    "rtl/test/tb_hdc_dyn_ttiles.sv",
    "tools/hdc_isa.py",
    "tools/hdc_timing.py",
    "tools/rtl_hdc_dyn_ttiles.py",
)]
OUT = ROOT / "results/rtl/hdc_dyn_ttiles.json"


def main():
    with tempfile.TemporaryDirectory(prefix="qwen-dyn-ttiles-") as tmp:
        binary = Path(tmp) / "sim.vvp"
        subprocess.run(["iverilog", "-g2012", "-s", "tb_hdc_dyn_ttiles", "-o", str(binary),
                        str(SOURCES[0]), str(SOURCES[1])], cwd=ROOT, check=True)
        cp = subprocess.run(["vvp", str(binary)], cwd=ROOT, capture_output=True,
                            text=True, check=True)
        if "PASS exact DYN_TTILES: 756 position/split cases, G4 and G6144" not in cp.stdout:
            raise RuntimeError(cp.stdout)
    cases = 0
    for groups in (4, 6144):
        for split in range(3 if groups == 4 else 12):
            f = {"me_tiles": 0, "me_d_tiles": I.DYN_TTILES, "me_k": 16,
                 "me_d_k": I.DYN_NONE, "me_wsrc": 1, "me_split": split}
            for pos in range(0, 8192, 137):
                rounds, _ = T.me_loop(f, [0] * 8, pos, groups)
                expected = pos // (I.W_LANES * (groups >> split)) + 1
                if rounds != expected:
                    raise AssertionError((groups, split, pos, rounds, expected))
                cases += 1
    record = {
        "status": "pass", "rtl_cases": 756, "timing_model_cases": cases,
        "groups": [4, 6144], "context_max_tested": 8191,
        "source_sha256": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                          for p in SOURCES},
        "claim_boundary": "Exact position-round count in a combinational RTL helper and timing "
                          "model. Full vector-core decode and shipped-shape token execution are not "
                          "proved by this focused gate."
    }
    OUT.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    print(cp.stdout.strip())
    print(f"PASS timing model: {cases} exact cases")


if __name__ == "__main__":
    main()
