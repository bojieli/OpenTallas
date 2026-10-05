#!/usr/bin/env python3
"""Reduced source-pinned m5 arithmetic to acceptance handoff gate."""
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
from rtl_hdc_qwen_m5_mac_reduce import RTL

SOURCES = [ROOT / p for p in (
    "rtl/hdc/ot_hdc_qwen_m5_result_tokens.sv",
    "rtl/hdc/ot_hdc_qwen_dflash_step_ctrl.sv",
    "rtl/hdc/ot_hdc_accept.sv",
    "rtl/test/tb_hdc_qwen_m5_arith_commit.sv",
    "rtl/test/tb_hdc_qwen_m5_result_tokens.sv",
)] + RTL
OUT = ROOT / "results/rtl/hdc_qwen_m5_arith_commit.json"


def main():
    with tempfile.TemporaryDirectory(prefix="qwen-m5-commit-") as tmp:
        binary = Path(tmp) / "sim.vvp"
        subprocess.run(["iverilog", "-g2012", "-s", "tb_hdc_qwen_m5_arith_commit",
                        "-o", str(binary), *map(str, SOURCES)], cwd=ROOT, check=True)
        cp = subprocess.run(["vvp", str(binary)], cwd=ROOT, capture_output=True,
                            text=True, check=True)
        expected = "PASS Qwen m5 arithmetic-to-commit: 8 result beats, 5 exact argmax tokens, accepted 2, KV drain barrier"
        if expected not in cp.stdout:
            raise RuntimeError(cp.stdout)
        scan_binary = Path(tmp) / "scan.vvp"
        subprocess.run(["iverilog", "-g2012", "-s", "tb_hdc_qwen_m5_result_tokens",
                        "-o", str(scan_binary), str(SOURCES[0]), str(SOURCES[4])],
                       cwd=ROOT, check=True)
        scan = subprocess.run(["vvp", str(scan_binary)], cwd=ROOT,
                              capture_output=True, text=True, check=True)
        if "PASS Qwen m5 running argmax: 3 vocabulary chunks" not in scan.stdout:
            raise RuntimeError(scan.stdout)
        subprocess.run(["verilator", "--lint-only", "-Wno-fatal", "-Wno-WIDTH",
                        "-Wno-TIMESCALEMOD", "--top-module", "ot_hdc_qwen_m5_result_tokens",
                        str(SOURCES[0])], cwd=ROOT, capture_output=True, text=True, check=True)
    record = {
        "status": "pass", "result_beats": 8, "verify_tokens": 5,
        "accepted_drafts": 2, "emitted_tokens": 3,
        "next_token": 101, "next_pos": 203, "kv_drain_barrier": "pass",
        "vocabulary_chunk_argmax": {"chunks": 3, "slots": 5, "status": "pass"},
        "source_sha256": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                          for p in [*SOURCES, Path(__file__)]},
        "claim_boundary": "Reduced m5 arithmetic/argmax/acceptance handoff. The drafter tokens and "
                          "KV drain handshake are scripted; the arithmetic receives decoded BF16 weights, "
                          "and its three-chunk running argmax is a tiny test vocabulary, not the full lm_head. "
                          "No full TP-2 "
                          "program, KV HBM, physical route, or shipped-shape token is exercised."
    }
    OUT.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    print(expected)
    print(scan.stdout.strip())


if __name__ == "__main__":
    main()
