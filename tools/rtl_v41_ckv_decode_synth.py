"""Bounded generic synthesis preflight for one factored CKV decoder."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
RTL = ROOT / "rtl/chip/ot_chip_v41x_ckv_fp4_decode.sv"
DEFAULT_YOSYS = Path("/home/ubuntu/.local/opentallas-tools/yosys-0.68/bin/yosys")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--yosys", default=os.environ.get("V41_CKV_YOSYS",
                   str(DEFAULT_YOSYS) if DEFAULT_YOSYS.exists() else "yosys"))
    p.add_argument("--output", type=Path,
                   default=ROOT / "results/rtl/v41x_ckv_decode_synth.json")
    args = p.parse_args()
    exe = shutil.which(args.yosys)
    if exe is None:
        raise RuntimeError(f"yosys unavailable: {args.yosys}")
    version = subprocess.run([exe, "-V"], check=True, capture_output=True,
                             text=True, timeout=10).stdout.strip()
    command = f"read_verilog -sv {RTL}; synth -top ot_chip_v41x_ckv_fp4_decode; stat"
    proc = subprocess.run([exe, "-Q", "-T", "-p", command], cwd=ROOT,
                          check=True, capture_output=True, text=True, timeout=120)
    section = proc.stdout.rsplit("=== ot_chip_v41x_ckv_fp4_decode ===", 1)[-1]
    counts = re.findall(r"\b(\d+) cells\b", section)
    if not counts:
        raise RuntimeError("decoder cell count missing from synthesis output")
    record = {
        "status": "generic_synthesis_only",
        "scope": "one combinational element decoder; no mapped library, floorplan, route or timing",
        "yosys_version": version,
        "source": str(RTL.relative_to(ROOT)),
        "source_sha256": hashlib.sha256(RTL.read_bytes()).hexdigest(),
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "generic_cells": int(counts[-1]),
        "check_errors": 0 if "Found and reported 0 problems" in proc.stdout else None,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    print(json.dumps(record, sort_keys=True))


if __name__ == "__main__":
    main()
