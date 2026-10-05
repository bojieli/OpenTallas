#!/usr/bin/env python3
"""Source-pinned Qwen DFlash block-5 draft/verify/commit control gate."""
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCES = [ROOT / p for p in (
    "rtl/hdc/ot_hdc_qwen_dflash_step_ctrl.sv",
    "rtl/hdc/ot_hdc_accept.sv",
    "rtl/test/tb_hdc_qwen_dflash_step_ctrl.sv",
    "tools/rtl_hdc_qwen_dflash_step_ctrl.py",
)]
OUT = ROOT / "results/rtl/hdc_qwen_dflash_step_ctrl.json"


def main():
    with tempfile.TemporaryDirectory(prefix="qwen-dflash-ctrl-") as tmp:
        binary = Path(tmp) / "sim.vvp"
        subprocess.run(["iverilog", "-g2012", "-s", "tb_hdc_qwen_dflash_step_ctrl",
                        "-o", str(binary), *map(str, SOURCES[:-1])], cwd=ROOT, check=True)
        cp = subprocess.run(["vvp", str(binary)], cwd=ROOT, capture_output=True, text=True, check=True)
        if "PASS Qwen DFlash controller: 3 accepted-prefix cases, KV drain barrier, early-done fault" not in cp.stdout:
            raise RuntimeError(cp.stdout)
        subprocess.run(["verilator", "--lint-only", "-Wno-fatal", "-Wno-WIDTH", "-Wno-TIMESCALEMOD",
                        "--top-module", "ot_hdc_qwen_dflash_step_ctrl", *map(str, SOURCES[:2])],
                       cwd=ROOT, capture_output=True, text=True, check=True)
    record = {"status": "pass", "block_slots": 5, "draft_tokens": 4,
              "accepted_prefix_cases": [0, 2, 4], "kv_drain_barrier": "pass",
              "incomplete_draft_fault": "pass",
              "source_sha256": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                                for p in SOURCES},
              "claim_boundary": "Reduced control gate: draft and target token inputs are scripted, KV drain is "
                                "a handshake, and no drafter/verify arithmetic, real KV HBM, UCIe, "
                                "full-shape token, or physical implementation is exercised."}
    OUT.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    print(cp.stdout.strip())


if __name__ == "__main__":
    main()
