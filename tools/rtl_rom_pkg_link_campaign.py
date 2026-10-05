#!/usr/bin/env python3
"""Simulate the ROM package-to-package link and check its latency law.

docs/ANALYTICAL_REPORT.md prices a hop between ROM packages at 209 ns plus
serialisation (links.rom_board_serdes: a 200 ns channel of 112G PAM4 SerDes with
RS(544,514) FEC, 4 cycles of clock-domain crossing and this endpoint's 5
cycles).  This campaign runs
rtl/rom/ot_rom_pkg_link.sv under Icarus, lints it under Verilator, and checks
that a message of F flits arrives with

    first-flit latency = TX_STAGES + CHANNEL_CYCLES + RX_STAGES + 1
    last-flit latency  = first-flit latency + F - 1

with a free-running receiver, and without loss or reordering under random
back-pressure.  CHANNEL_CYCLES stands in for the analog PHY, FEC and flight
time plus the clock-domain crossing (200 + 4 cycles at 1 GHz, so the first flit
lands at the technology's 209 ns hop); only the digital framing, credit flow and
cut-through are logic.  The flit stays 1,800 bytes (the package's raw lane rate
at 1 GHz); the net rate after FEC and transcoding is 1.69 TB/s.
"""
import argparse
import hashlib
import json
import re
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RTL = ROOT / "rtl/rom/ot_rom_pkg_link.sv"
TB = ROOT / "rtl/test/tb_rom_pkg_link.sv"
OUT = ROOT / "results/rtl/rom_pkg_link_campaign.json"
# Must match the testbench parameters.
FLIT_BYTES, TX, CH, RX, CREDITS = 1800, 2, 204, 2, 256
OUT_STAGE = 1   # registered output, added after ASAP7 routing found the read mux critical
FIRST = TX + CH + RX + OUT_STAGE
LINT_FLAGS = ("-Wall", "-Wno-DECLFILENAME", "-Wno-UNUSED", "-Wno-WIDTH")
CASE = re.compile(r"CASE label=(\S+) flits=(\d+) first_latency=(\d+) last_latency=(\d+) "
                  r"stalls=(\d+) errors=(\d+)")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run() -> dict:
    with tempfile.TemporaryDirectory() as scratch:
        image = Path(scratch) / "tb.vvp"
        subprocess.run(["iverilog", "-g2012", "-o", str(image), str(RTL), str(TB)], check=True)
        sim = subprocess.run(["vvp", "-n", str(image)], check=True, capture_output=True, text=True)
    lint = subprocess.run(["verilator", "--lint-only", *LINT_FLAGS, "--top-module", "ot_rom_pkg_link", str(RTL)],
                          capture_output=True, text=True)
    cases = []
    for line in sim.stdout.splitlines():
        m = CASE.match(line.strip())
        if not m:
            continue
        label, flits, first, last, stalls, errors = m.groups()
        flits, first, last, stalls, errors = map(int, (flits, first, last, stalls, errors))
        free = label != "backpressure"
        ok = errors == 0 and (not free or (first == FIRST and last == FIRST + flits - 1))
        cases.append({"label": label, "flits": flits, "message_bytes": flits * FLIT_BYTES,
                      "first_flit_latency_cycles": first, "last_flit_latency_cycles": last,
                      "expected_last_flit_latency_cycles": FIRST + flits - 1 if free else None,
                      "credit_stalls": stalls, "scoreboard_errors": errors, "pass": ok})
    summary_ok = "SUMMARY errors=0" in sim.stdout
    status = "pass" if cases and all(c["pass"] for c in cases) and summary_ok and lint.returncode == 0 else "fail"
    one_user = next(c for c in cases if c["label"] == "one_user")
    return {
        "schema": "opentallas.rom-pkg-link-campaign.v1",
        "status": status,
        "claim_boundary": "functional RTL of the digital link endpoint: framing, credits, cut-through. "
                          "CHANNEL_CYCLES is a delay-line stand-in for SerDes, FEC, flight and the clock-domain "
                          "crossing (200 + 4 cycles); no PHY. Credits return immediately here; a real return "
                          "crosses the channel, so full rate needs ~418 flits of receive buffer, not 256.",
        "technology_hop_s": json.loads((ROOT / "configs/hardware/technology.json").read_text())[
            "links"]["rom_board_serdes"]["hop_latency_s"]["value"],
        "parameters": {"flit_bytes": FLIT_BYTES, "tx_stages": TX, "channel_cycles": CH, "rx_stages": RX,
                       "credits": CREDITS, "clock_hz": 1e9},
        "digital_endpoint_cycles": TX + RX + OUT_STAGE,
        "one_user_hidden_state_latency_ns": one_user["last_flit_latency_cycles"],
        "cases": cases,
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
    print(result["status"], "one user", result["one_user_hidden_state_latency_ns"], "ns",
          [(c["label"], c["last_flit_latency_cycles"]) for c in result["cases"]])
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
