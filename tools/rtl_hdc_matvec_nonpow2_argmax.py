#!/usr/bin/env python3
"""Source-pinned non-power-of-two Qwen matrix argmax tree gate."""
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path

import rtl_hdc_decode_campaign as C

ROOT = Path(__file__).resolve().parents[1]
SOURCES = [ROOT / "rtl/test/tb_hdc_matvec_nonpow2_argmax.sv", *C.HDC, *C.PIPES,
           Path(__file__)]
OUT = ROOT / "results/rtl/hdc_matvec_nonpow2_argmax.json"


def main():
    with tempfile.TemporaryDirectory(prefix="qwen-argmax-nonpow2-") as tmp:
        binary = Path(tmp) / "sim.vvp"
        cp = subprocess.run(["iverilog", "-g2012", f"-I{C.ISA_SVH.parent}",
                             "-s", "tb_hdc_matvec_nonpow2_argmax", "-o", str(binary),
                             *map(str, SOURCES[:-1])], cwd=ROOT, capture_output=True,
                            text=True)
        if cp.returncode:
            raise RuntimeError(cp.stdout + cp.stderr)
        cp = subprocess.run(["vvp", str(binary)], cwd=ROOT,
                            capture_output=True, text=True, check=True)
        expected = "PASS non-power-of-two matvec argmax: G3/W2, padded leaves invalid, winner row 33"
        if expected not in cp.stdout:
            raise RuntimeError(cp.stdout)
    record = {
        "status": "pass", "groups": 3, "lanes_per_group": 2,
        "padded_leaf_count": 8, "expected_winner_row": 33,
        "source_sha256": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                          for p in SOURCES},
        "claim_boundary": "Isolated registered compare-tree gate at its result boundary. "
                          "The six scores and mask are forced in a testbench; matrix MAC, full G6144 "
                          "elaboration, full-vocabulary lm_head and shipped-shape token are not exercised."
    }
    OUT.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    print(expected)


if __name__ == "__main__":
    main()
