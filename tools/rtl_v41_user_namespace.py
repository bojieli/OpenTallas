#!/usr/bin/env python3
"""Run the V4.1 package-controller 866-user namespace gate."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCES = (Path("rtl/rom/ot_rom_pkg_ctrl_x.sv"), Path("rtl/test/tb_v41_user_namespace.sv"))
PASS = "PASS v41 user namespace ids 1/257/865, SOURCE 866 contexts, invalid 866 rejected"


def run(output: Path) -> dict:
    tests = {}
    with tempfile.TemporaryDirectory(prefix="v41_user_namespace_") as tmp:
        for nw, flag in ((16, ()), (21, ("-DFULL_NW21",))):
            binary = Path(tmp) / f"namespace_{nw}.vvp"
            compile_cmd = ["iverilog", "-g2012", *flag, "-s", "tb_v41_user_namespace",
                           "-o", str(binary), *(str(ROOT / p) for p in SOURCES)]
            subprocess.run(compile_cmd, check=True, capture_output=True, text=True)
            verdict = subprocess.run(["vvp", str(binary)], check=True, capture_output=True, text=True)
            if PASS not in verdict.stdout:
                raise RuntimeError(f"NW={nw} did not print the exact namespace verdict: {verdict.stdout}")
            tests[str(nw)] = {"pass": True, "source_users": 866, "distinct_users": [1, 257, 865],
                              "invalid_user_rejected": 866,
                              "side_and_kv_addresses_checked": True,
                              "header_user_roundtrip_checked": True}
    result = {
        "scope": "package-controller RTL only; die host wiring, HBM capacity, scheduling and throughput not proven",
        "source_sha256": {str(p): hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in SOURCES},
        "tests": tests,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "results/rtl/v41_user_namespace.json")
    args = parser.parse_args()
    result = run(args.output)
    print(json.dumps({"output": str(args.output), "tests": result["tests"]}, sort_keys=True))
