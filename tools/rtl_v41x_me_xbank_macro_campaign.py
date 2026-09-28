#!/usr/bin/env python3
"""Source-pinned exact-order gates for the grouped ASAP7 ME SRAM abstract."""
import hashlib
import json
import re
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RTL = ROOT / "rtl/hdc/v41x/ot_hdc_v41x_me_xbank_macro.sv"
MACRO = ROOT / "physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v"
DATA = ROOT / "rtl/test/data/v41x_me_xbank_l0_real.hex"
CASES = (
    ("two_group", "tb_v41x_me_two_group", r"ME_TWO_GROUP_PASS load_cycles=2048 reads=8192 errors=0"),
    ("two_group_wide", "tb_v41x_me_two_group_wide", r"ME_TWO_GROUP_WIDE_PASS preload_cycles=128 reads=8192 errors=0"),
    ("segments_mp2", "tb_v41x_me_xbank", r"ME_XBANK_PASS kmax=5120 lanes=64 mp=2 reads=128000 errors=0"),
)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(output: Path) -> dict:
    pins = {str(p.relative_to(ROOT)): sha(p) for p in (RTL, MACRO, DATA)}
    cases = {}
    with tempfile.TemporaryDirectory(prefix="v41_me_macro_") as tmp:
        work = Path(tmp)
        for name, top, marker in CASES:
            tb = ROOT / f"rtl/test/{top}.sv"
            pins[str(tb.relative_to(ROOT))] = sha(tb)
            source = tb.read_text().replace("ot_hdc_v41x_me_xbank #", "ot_hdc_v41x_me_xbank_macro #")
            if source == tb.read_text():
                raise RuntimeError(f"{top}: original instance not found")
            derived_tb = work / f"{top}.sv"
            derived_tb.write_text(source)
            binary = work / f"{top}.vvp"
            subprocess.run(["iverilog", "-g2012", "-s", top, "-o", str(binary),
                            str(RTL), str(MACRO), str(derived_tb)], check=True,
                           capture_output=True, text=True)
            arg = "ME_DATA" if name == "segments_mp2" else "DATA"
            proc = subprocess.run(["vvp", str(binary), f"+{arg}={DATA}"],
                                  check=True, capture_output=True, text=True)
            if not re.search(marker, proc.stdout):
                raise RuntimeError(f"{name}: expected marker absent: {proc.stdout[-2000:]}")
            cases[name] = {"status": "pass", "marker": marker,
                           "stdout_sha256": hashlib.sha256(proc.stdout.encode()).hexdigest()}
    record = {
        "schema": "opentallas.rtl.v41x_me_xbank_macro.v1",
        "status": "pass",
        "claim_scope": "Analytical ASAP7 128x256 1R1W SRAM-model exact-order gate for two TP4 wo_a activation groups, wide preload, and both ME positions. No adapter, timing, foundry, or token-rate claim.",
        "macro_instances_at_mp2": 16,
        "macro_placement_area_um2": 16 * 3891.57696,
        "macro_signal_pins_total_internal": 16 * 819,
        "source_sha256": pins,
        "cases": cases,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    return record


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, default=ROOT / "results/rtl/v41x_me_xbank_macro_campaign.json")
    args = ap.parse_args()
    print(json.dumps(run(args.output), indent=2))
