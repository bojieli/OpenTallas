#!/usr/bin/env python3
"""Check run-time PHY-delay taps of the RTL package link."""
import hashlib
import json
import re
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LINK = ROOT / "rtl/rom/ot_rom_pkg_link.sv"
TB = ROOT / "rtl/test/tb_rom_pkg_link.sv"
OUT = ROOT / "results/rtl/rom_pkg_link_delay_sweep.json"
CASE = re.compile(r"CASE label=(\S+) flits=(\d+) first_latency=(\d+) last_latency=(\d+) stalls=(\d+) errors=(\d+)")


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, default=OUT)
    args = ap.parse_args()
    with tempfile.TemporaryDirectory() as tmp:
        image = Path(tmp) / "link.vvp"
        subprocess.run(["iverilog", "-g2012", "-Ptb_rom_pkg_link.DYNAMIC_DELAY=1", "-o", str(image),
                        str(LINK), str(TB)], check=True)
        points = []
        for ch in (30, 109, 228):
            sim = subprocess.run(["vvp", "-n", str(image), f"+LINK_CH={ch}"], check=True,
                                 capture_output=True, text=True)
            cases = [{"label": m[0], "flits": int(m[1]), "first_latency_cycles": int(m[2]),
                      "last_latency_cycles": int(m[3]), "credit_stalls": int(m[4]),
                      "scoreboard_errors": int(m[5])} for m in CASE.findall(sim.stdout)]
            ok = len(cases) == 4 and "SUMMARY errors=0" in sim.stdout and all(
                c["scoreboard_errors"] == 0 for c in cases) and cases[0]["first_latency_cycles"] == ch + 5
            points.append({"channel_cycles": ch, "first_flit_cycles": cases[0]["first_latency_cycles"],
                           "two_half_link_cycles_before_router": 2 * cases[0]["first_latency_cycles"],
                           "two_half_link_ns_at_assumed_0p92ns_before_router": round(
                               2 * cases[0]["first_latency_cycles"] * 0.92, 2),
                           "cases": cases, "pass": ok})
    record = {
        "schema": "opentallas.rom-pkg-link-delay-sweep.v1",
        "status": "pass" if all(p["pass"] for p in points) else "fail",
        "claim_boundary": "Icarus RTL link endpoint with a selected delay tap, 256-flit receive credit FIFO, "
                          "and immediate credit return. The 0.92 ns clock is an assumed conversion for the "
                          "array delay setting, not link timing closure; router cycles and PHY are excluded.",
        "points": points,
        "input_sha256": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                         for p in (LINK, TB, Path(__file__))},
    }
    args.output.write_text(json.dumps(record, indent=2) + "\n")
    print(record["status"], [(p["channel_cycles"], p["first_flit_cycles"]) for p in points])
    return 0 if record["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
