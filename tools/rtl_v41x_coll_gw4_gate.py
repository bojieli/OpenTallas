#!/usr/bin/env python3
"""Reproduce focused exact GW4 engine, transpose and DMA boundary gates."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERILATOR = Path("/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator")
OUT = ROOT / "results/rtl/v41x_coll_gw4_gate.json"
SOURCES = [
    "rtl/chip/ot_chip_v41x_coll_transpose.sv",
    "rtl/chip/ot_chip_v41x_coll_dma.sv",
    "rtl/rom/ot_rom_oneshot_px.sv",
    "rtl/hdc/ot_hdc_fastfp.sv",
    "rtl/proto/ot_fp32_add_rne_pipe.sv",
    "rtl/test/tb_v41x_coll_transpose.sv",
    "rtl/test/tb_v41x_coll_dma_gw4.sv",
    "rtl/test/tb_v41x_coll_gw4_backpressure.sv",
    "tools/rtl_v41x_coll_gw4_gate.py",
]


def run_case(scratch: Path, top: str, words: int, sources: list[str], pattern: str, pipe: int = 0) -> dict:
    mdir = scratch / f"{top}_{words}_p{pipe}"
    cmd = [str(VERILATOR), "--binary", "--timing", "-j", "4", "-Wno-fatal",
           "-Wno-TIMESCALEMOD", "--top-module", top, f"-GWORDS={words}",
           "--Mdir", str(mdir), *[str(ROOT / p) for p in sources]]
    if pipe:
        cmd.insert(cmd.index("--Mdir"), "-GPIPE=1")
    build = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    if build.returncode:
        raise RuntimeError(f"{top}/{words} compile failed:\n{build.stderr[-4000:]}")
    sim = subprocess.run([str(mdir / f"V{top}")], cwd=ROOT, capture_output=True, text=True)
    if sim.returncode:
        raise RuntimeError(f"{top}/{words} exact gate failed:\n{sim.stdout[-2000:]}\n{sim.stderr[-2000:]}")
    match = re.search(pattern, sim.stdout)
    if not match:
        raise AssertionError(f"{top}/{words} did not report PASS: {sim.stdout[-2000:]}")
    result = {k: int(v) for k, v in match.groupdict().items()}
    assert result["words"] == words
    assert result["writes"] == 4 * words
    return {"top": top, "words": words, "pipe": pipe, "passed": True, "metrics": result}


def run(scratch: Path) -> dict:
    version = subprocess.check_output([str(VERILATOR), "--version"], text=True).strip()
    cases = []
    transpose = ["rtl/chip/ot_chip_v41x_coll_transpose.sv", "rtl/test/tb_v41x_coll_transpose.sv"]
    dma = ["rtl/chip/ot_chip_v41x_coll_transpose.sv", "rtl/chip/ot_chip_v41x_coll_dma.sv",
           "rtl/test/tb_v41x_coll_dma_gw4.sv"]
    backpressure = ["rtl/chip/ot_chip_v41x_coll_transpose.sv", "rtl/rom/ot_rom_oneshot_px.sv",
                    "rtl/hdc/ot_hdc_fastfp.sv", "rtl/proto/ot_fp32_add_rne_pipe.sv",
                    "rtl/test/tb_v41x_coll_gw4_backpressure.sv"]
    for words in (1, 2, 5, 80, 266):
        cases.append(run_case(scratch, "tb_v41x_coll_transpose", words, transpose,
                              r"TRANSPOSE_PASS words=(?P<words>\d+) writes=(?P<writes>\d+) stalls=(?P<stalls>\d+) holds=(?P<holds>\d+) cycles=(?P<cycles>\d+)"))
    for words in (80, 266):
        cases.append(run_case(scratch, "tb_v41x_coll_dma_gw4", words, dma,
                              r"CDMA_GW4_PASS words=(?P<words>\d+) committed=(?P<writes>\d+) held=(?P<held>\d+) cycles=(?P<cycles>\d+)"))
        cases.append(run_case(scratch, "tb_v41x_coll_dma_gw4", words, dma,
                              r"CDMA_GW4_PASS words=(?P<words>\d+) committed=(?P<writes>\d+) held=(?P<held>\d+) cycles=(?P<cycles>\d+)", pipe=1))
    cases.append(run_case(scratch, "tb_v41x_coll_gw4_backpressure", 266, backpressure,
                          r"GW4_BACKPRESSURE_PASS words=(?P<words>\d+) writes=(?P<writes>\d+) in_hold=(?P<in_hold>\d+) out_hold=(?P<out_hold>\d+) cycles=(?P<cycles>\d+)"))
    assert all(c["passed"] for c in cases)
    return {"schema": "v41x_coll_gw4_gate_v1", "verilator": version,
            "scope": "exact standalone engine/transpose/DMA with synthetic words; elastic and registered always-ready bank sinks; no full-token, die route or physical VM claim",
            "contract": {"N": 4, "FW": 512, "VM_bank": "word_address_low_2_bits",
                         "VM_write_words_per_cycle": 4, "VM_write_word_bits": 512,
                         "VM_write_bus_bits": 2048, "bank_commit_pipeline_cycles": 2,
                         "full_width_physical_route": "open", "full_shape_transpose_OUT_PIPE": 1,
                         "blocked_COLL_v1": True},
            "source_sha256": {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in SOURCES},
            "cases": cases}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scratch", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    args.scratch.mkdir(parents=True, exist_ok=True)
    record = run(args.scratch)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    print(json.dumps(record["cases"], indent=2))


if __name__ == "__main__":
    main()
