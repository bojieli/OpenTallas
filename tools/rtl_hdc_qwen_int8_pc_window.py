#!/usr/bin/env python3
"""Run the bounded INT8 code/scale pseudo-channel window RTL gate."""
import hashlib
import json
import re
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/rtl/qwen_o4_hbm_pc_window.json"
SOURCES = [ROOT / p for p in (
    "rtl/hdc/hbm/ot_hdc_qwen_int8_pc_window.sv",
    "rtl/test/tb_hdc_qwen_int8_pc_window.sv",
    "rtl/hdc/ot_hdc_core_vector_weight.sv",
    "tools/rtl_hdc_qwen_int8_pc_window.py",
)]


def main():
    with tempfile.TemporaryDirectory(prefix="qwen_int8_pc_window_") as tmp:
        binary = Path(tmp) / "sim.vvp"
        build = subprocess.run(["iverilog", "-g2012", "-s", "tb_hdc_qwen_int8_pc_window",
                                "-o", str(binary), str(SOURCES[0]), str(SOURCES[1])],
                               cwd=ROOT, capture_output=True, text=True)
        run = subprocess.run(["vvp", str(binary)], cwd=ROOT, capture_output=True, text=True) if build.returncode == 0 else None
    m = re.search(r"PASS Qwen INT8 PC-local HBM window: (\d+) sectors, (\d+) cycles, exact codes/scales",
                  run.stdout if run else "")
    ok = build.returncode == 0 and run is not None and run.returncode == 0 and m is not None
    record = {
        "schema": "opentallas.qwen-o4-hbm-pc-window.v1",
        "status": "pass" if ok else "fail",
        "configuration": {"groups": 4, "lanes_per_group": 16, "pseudo_channels": 2,
                          "hbm_sector_address_bits": 28, "window_words": 2,
                          "weight_bytes_per_word": 64, "scale_bytes_per_word": 128},
        "observed": {"sector_reads": int(m.group(1)), "preload_cycles": int(m.group(2))} if m else {},
        "claim_boundary": "Standalone bounded PC-local INT8 code/BF16-scale supply with exact 32-byte sector reconstruction and one-cycle synchronous core ports. Synthetic 2-word operation only; no same-program package token, full G6144 bandwidth, HBM controller or P&R claim.",
        "input_sha256": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in SOURCES},
        "build_stderr": build.stderr[-1000:],
        "simulation_stdout": run.stdout[-1000:] if run else "",
        "simulation_stderr": run.stderr[-1000:] if run else "",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    print(f"{OUT}: {record['status']}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
