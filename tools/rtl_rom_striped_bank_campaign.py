#!/usr/bin/env python3
"""Simulate striped versus dedicated expert banks and check the schedules.

docs/ANALYTICAL_REPORT.md credits the redesigned ROM machine with reading a
token's selected experts at the whole die's read rate (rom.expert_bank_pooling
= "striped").  This campaign runs rtl/rom/ot_rom_striped_expert_reader.sv under
Icarus, lints it under Verilator, and checks every scoreboarded run against the
closed forms the framework assumes:

    striped    cycles = k * EXPERT_WORDS / BANKS + overhead
    dedicated  cycles = max_bank_load * EXPERT_WORDS + overhead

where max_bank_load is the most selected experts sharing one dedicated bank.
Functional RTL simulation only: no macro, area, timing or energy.
"""
import argparse
import hashlib
import json
import re
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RTL = ROOT / "rtl/rom/ot_rom_striped_expert_reader.sv"
TB = ROOT / "rtl/test/tb_rom_striped_expert_reader.sv"
OUT = ROOT / "results/rtl/rom_striped_bank_campaign.json"
# Must match the testbench parameters.
BANKS, EXPERTS, EXPERT_WORDS, MAX_SELECT, LAT = 8, 48, 64, 6, 2
EW = (EXPERTS - 1).bit_length()
OVERHEAD = LAT + 2   # sense pipeline plus issue and drain handshakes
# -Wall minus two classes, both intentional in a behavioural block: WIDTH (integer
# parameters mixed with narrow indices) and BLKSEQ (per-cycle temporaries).
LINT_FLAGS = ("-Wall", "-Wno-DECLFILENAME", "-Wno-UNUSED", "-Wno-WIDTH", "-Wno-BLKSEQ")
CASE = re.compile(r"CASE label=(\S+) mode=(\S+) k=(\d+) ids=([0-9a-f]+) cycles=(\d+) "
                  r"words=(\d+) serialised=(\d+) errors=(\d+)")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def unpack(ids_hex: str, k: int) -> list[int]:
    value = int(ids_hex, 16)
    return [(value >> (j * EW)) & ((1 << EW) - 1) for j in range(k)]


def expected_cycles(mode: str, ids: list[int]) -> int:
    if mode == "striped":
        return len(ids) * EXPERT_WORDS // BANKS + OVERHEAD
    load = max(sum(1 for e in ids if e % BANKS == b) for b in range(BANKS))
    return load * EXPERT_WORDS + OVERHEAD


def run() -> dict:
    with tempfile.TemporaryDirectory() as scratch:
        image = Path(scratch) / "tb.vvp"
        subprocess.run(["iverilog", "-g2012", "-o", str(image), str(RTL), str(TB)], check=True)
        sim = subprocess.run(["vvp", "-n", str(image)], check=True, capture_output=True, text=True)
    lint = subprocess.run(["verilator", "--lint-only", *LINT_FLAGS,
                           "--top-module", "ot_rom_striped_expert_reader", str(RTL)],
                          capture_output=True, text=True)
    cases = []
    for line in sim.stdout.splitlines():
        m = CASE.match(line.strip())
        if not m:
            continue
        label, mode, k, ids_hex, cycles, words, serialised, errors = m.groups()
        ids = unpack(ids_hex, int(k))
        want = expected_cycles(mode, ids)
        cases.append({
            "label": label, "mode": mode, "experts": ids, "cycles": int(cycles),
            "expected_cycles": want, "words": int(words), "expected_words": len(ids) * EXPERT_WORDS,
            "dedicated_serialised_experts": int(serialised), "scoreboard_errors": int(errors),
            "pass": int(cycles) == want and int(words) == len(ids) * EXPERT_WORDS and int(errors) == 0,
        })
    striped = [c for c in cases if c["mode"] == "striped" and len(c["experts"]) == MAX_SELECT]
    dedicated = [c for c in cases if c["mode"] == "dedicated" and len(c["experts"]) == MAX_SELECT]
    summary_ok = "SUMMARY" in sim.stdout and "errors=0" in sim.stdout
    status = "pass" if cases and all(c["pass"] for c in cases) and summary_ok and lint.returncode == 0 else "fail"
    return {
        "schema": "opentallas.rom-striped-bank-campaign.v1",
        "status": status,
        "claim_boundary": "functional RTL simulation of the striped-bank address map and stream schedule; "
                          "behavioural banks, no macro, area, timing or read energy",
        "parameters": {"banks": BANKS, "experts": EXPERTS, "expert_words": EXPERT_WORDS,
                       "max_select": MAX_SELECT, "sense_latency": LAT, "overhead_cycles": OVERHEAD},
        "cases": cases,
        "striped_cycles_six_experts": sorted({c["cycles"] for c in striped}),
        "dedicated_cycles_six_experts": sorted({c["cycles"] for c in dedicated}),
        "worst_dedicated_over_striped": max(c["cycles"] for c in dedicated) / min(c["cycles"] for c in striped),
        "verilator_lint": {"returncode": lint.returncode, "flags": list(LINT_FLAGS),
                           "messages": lint.stderr.strip().splitlines()[:20]},
        "input_sha256": {str(p.relative_to(ROOT)): sha(p) for p in (RTL, TB, Path(__file__))},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUT)
    args = parser.parse_args()
    result = run()
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(result["status"], "striped", result["striped_cycles_six_experts"],
          "dedicated", result["dedicated_cycles_six_experts"],
          f"worst {result['worst_dedicated_over_striped']:.2f}x")
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
