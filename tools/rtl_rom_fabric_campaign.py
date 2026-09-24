#!/usr/bin/env python3
"""Unit verification of the ROM-array fabric RTL (docs/ROM_ARRAY_FABRIC_RTL.md).

Runs, from the repository root:

1. a Verilator lint of the packet router (rtl/rom/ot_rom_fabric_router.sv)
   and the package controller (rtl/rom/ot_rom_pkg_ctrl.sv, in the superset
   configuration that is routed: SOURCE with a 4-part reduction, sending
   HIDDEN and RESULT messages and combining a running argmax);
2. the router's random-traffic testbench (rtl/test/tb_rom_fabric_router.sv)
   under Icarus over several port counts, buffer depths, receiver readiness
   levels and seeds, including the routed width (512-bit flits, 5 ports).
   Each run checks credits, payload integrity, wormhole contiguity, per-input
   ordering on every output, exact multicast delivery sets and drops.

Token-level verification of the controller and of the router inside an array
of decode cores is tools/rtl_hdc_array_campaign.py.  Writes
results/rtl/rom_fabric_campaign.json.
"""
import argparse
import hashlib
import json
import re
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/rtl/rom_fabric_campaign.json"
ROUTER = ROOT / "rtl/rom/ot_rom_fabric_router.sv"
CTRL = ROOT / "rtl/rom/ot_rom_pkg_ctrl.sv"
TB = ROOT / "rtl/test/tb_rom_fabric_router.sv"
LINT_FLAGS = ("-Wall", "-Wno-DECLFILENAME", "-Wno-UNUSED", "-Wno-WIDTH")
CTRL_PARAMS = {"SOURCE": 1, "RESULT_PARTS": 4, "SEND_HIDDEN": 1, "SEND_RESULT": 1, "COMBINE_IN": 1,
               "ROW0": 1024, "TXB": 8}
# (ports, flit bits, buffer, packets per input, receiver readiness percent, seed)
RUNS = [(5, 64, 4, 400, 70, 1), (5, 64, 4, 400, 70, 2), (5, 64, 4, 400, 30, 3), (5, 64, 4, 400, 100, 4),
        (3, 64, 2, 400, 60, 5), (8, 64, 4, 300, 70, 6), (8, 64, 1, 300, 80, 7), (5, 512, 4, 150, 70, 8)]
RES = re.compile(r"ROUTER_TB ports=(\d+) buf=(\d+) packets=(\d+) multicast_packets=(\d+) dropped=(\d+) "
                 r"sent_flits=(\d+) received_flits=(\d+) cycles=(\d+) errors=(\d+)")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def router_run(scratch: Path, np_, fw, buf, npkt, ready, seed) -> dict:
    vvp = scratch / f"r{np_}_{fw}_{buf}_{seed}.vvp"
    subprocess.run(["iverilog", "-g2012", "-o", str(vvp), f"-Ptb_rom_fabric_router.NP={np_}",
                    f"-Ptb_rom_fabric_router.FW={fw}", f"-Ptb_rom_fabric_router.BUF={buf}",
                    f"-Ptb_rom_fabric_router.NPKT={npkt}", f"-Ptb_rom_fabric_router.READY_PCT={ready}",
                    f"-Ptb_rom_fabric_router.SEED={seed}", str(TB), str(ROUTER)], check=True)
    out = subprocess.run(["vvp", "-n", str(vvp)], check=True, capture_output=True, text=True).stdout
    m = RES.search(out)
    ports, b, pk, mc, dr, sent, recv, cyc, err = map(int, m.groups())
    return {"ports": ports, "flit_bits": fw, "buffer_flits": b, "ready_percent": ready, "seed": seed,
            "packets": pk, "multicast_packets": mc, "dropped_packets": dr, "sent_flits": sent,
            "delivered_flits": recv, "cycles": cyc, "errors": err, "pass": "PASS" in out and err == 0}


def run() -> dict:
    lint = {}
    for name, src, params in (("ot_rom_fabric_router", ROUTER, {}), ("ot_rom_pkg_ctrl", CTRL, CTRL_PARAMS)):
        r = subprocess.run(["verilator", "--lint-only", *LINT_FLAGS, "--top-module", name,
                            *(f"-G{k}={v}" for k, v in params.items()), str(src)], capture_output=True, text=True)
        lint[name] = {"returncode": r.returncode, "parameters": params,
                      "messages": r.stderr.strip().splitlines()[:20]}
    with tempfile.TemporaryDirectory() as tmp, ThreadPoolExecutor(len(RUNS)) as pool:
        runs = list(pool.map(lambda c: router_run(Path(tmp), *c), RUNS))
    ok = all(r["pass"] for r in runs) and all(v["returncode"] == 0 for v in lint.values())
    return {
        "schema": "opentallas.rom-fabric-campaign.v1",
        "status": "pass" if ok else "fail",
        "claim_boundary": "functional RTL simulation (Icarus) of the packet router under random traffic and "
                          "a Verilator lint of the router and the package controller; token-level results "
                          "are results/rtl/hdc_array_campaign.json, clock rate the ASAP7 physical records.",
        "verilator_lint": {"flags": list(LINT_FLAGS), **lint},
        "router_random_traffic": runs,
        "input_sha256": {str(p.relative_to(ROOT)): sha(p) for p in (ROUTER, CTRL, TB, Path(__file__))},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--output", type=Path, default=OUT)
    args = parser.parse_args()
    result = run()
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    for r in result["router_random_traffic"]:
        print("pass" if r["pass"] else "FAIL", {k: r[k] for k in ("ports", "flit_bits", "buffer_flits",
                                                                  "ready_percent", "packets", "multicast_packets",
                                                                  "dropped_packets", "cycles", "errors")})
    print(result["status"], "lint", {k: v["returncode"] for k, v in result["verilator_lint"].items() if k != "flags"})
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
