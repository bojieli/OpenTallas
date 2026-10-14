#!/usr/bin/env python3
"""S81 PQ core cluster dsfd_sp_pq: lockstep bench against the FLAT v14 screen (s81-pqroot 2026-10-13).

REFERENCE  ot_v41_pqc_spine_screen of physical/s81_pq_xrv/pinned (the flat, pre-tile spine v14; XRV 1, the screen shape
           PHW 6 / SAW 8 / VAW 19 / VRD 64 / KMAX 256 / R 16 / PQ 1 / XCAP 16).
DUT        rtl/dsrom_sys/s81_ph/pq/dsfd_sp_pq.sv (wires over the fixed-name tile tops of physical/s81_pq_hier/pinned)
           in rtl/test/dsrom_sys/dsfd_sp_pq_screen_fix.sv (the three ROMs as the screen's two-cycle ROM models).
Both are driven with the same pins every cycle by rtl/test/dsrom_sys/tb_sp_pq_lockstep.cpp (legal constrained-random
programs) and EVERY output is compared every cycle.

    sp_pq_lockstep.py --work W [--mut CTL|IX|QB|RET|BC|AQ] [--seeds N] [--ops N] [--jobs J]

Prints the bench's 'SP_PQ_LOCKSTEP PASS exact=<compared cycles>' / 'SP_PQ_LOCKSTEP FAIL <first difference>' line and
exits with its status.  --mut builds the DUT with one tile mutant (OT_PQC_MUT_* / OT_AQ12T_MUT_RA): it must FAIL.
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VERILATOR = os.environ.get("OT_VERILATOR") or os.path.expanduser("~/.local/opentallas-tools/verilator-5.050/bin/verilator")
REF_PIN = ROOT / "physical/s81_pq_xrv/pinned"
DUT_PIN = ROOT / "physical/s81_pq_hier/pinned"
TB = ROOT / "rtl/test/dsrom_sys/tb_sp_pq_lockstep.cpp"
MUT = {"CTL": "OT_PQC_MUT_CTL", "IX": "OT_PQC_MUT_IX", "QB": "OT_PQC_MUT_QB", "RET": "OT_PQC_MUT_RET",
       "BC": "OT_PQC_MUT_BC", "AQ": "OT_AQ12T_MUT_RA"}


def srcs(pin: Path, extra=()):
    s = sorted(pin.rglob("*.sv"), key=lambda p: (0 if p.name == "ot_v41_pqc_tile_tops.sv" else 1, str(p)))
    return [*s, *extra]


def sh(cmd, log: Path):
    p = subprocess.run(cmd, capture_output=True, text=True)
    log.write_text(" ".join(map(str, cmd)) + "\n" + p.stdout + p.stderr)
    if p.returncode:
        print(f"BUILD FAIL ({log}):\n" + (p.stdout + p.stderr)[-3000:], flush=True)
        sys.exit(2)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", type=Path, required=True)
    ap.add_argument("--mut", choices=sorted(MUT))
    ap.add_argument("--seeds", type=int, default=24)
    ap.add_argument("--seed0", type=int, default=1)
    ap.add_argument("--ops", type=int, default=40)
    ap.add_argument("--jobs", type=int, default=16)
    a = ap.parse_args()
    w = a.work.resolve()
    w.mkdir(parents=True, exist_ok=True)
    vroot = re.search(r"VERILATOR_ROOT\s*=\s*(\S+)", subprocess.check_output([VERILATOR, "-V"], text=True)).group(1)
    common = [VERILATOR, "--cc", "-O3", "-Wno-fatal", "-Wno-lint", "-Wno-style", "-Wno-TIMESCALEMOD", "--x-assign", "0",
              "--x-initial", "0"]
    builds = {
        "ref": (["--top-module", "ot_v41_pqc_spine_screen", "-GXRV=1", "+define+OT_PQ_ROM_PORTS"], srcs(REF_PIN)),
        "dut": (["--top-module", "dsfd_sp_pq_screen_fix", "+define+OT_PQ_ROM_PORTS"] +
                ([f"+define+{MUT[a.mut]}"] if a.mut else []),
                srcs(DUT_PIN, [ROOT / "rtl/dsrom_sys/s81_ph/pq/dsfd_sp_pq.sv",
                               ROOT / "rtl/test/dsrom_sys/dsfd_sp_pq_screen_fix.sv"])),
    }
    libs = []
    for name, (args, ss) in builds.items():
        md = w / name
        sh([*common, "--prefix", f"V{name}", "--Mdir", str(md), *args, *map(str, ss)], w / f"{name}.verilate.log")
        sh(["make", "-C", str(md), "-f", f"V{name}.mk", f"-j{a.jobs}", f"V{name}__ALL.a", "OPT_FAST=-O2", "OPT_SLOW=-O1"],
           w / f"{name}.make.log")
        libs.append(md / f"V{name}__ALL.a")
    exe = w / "tb"
    sh(["g++", "-std=c++20", "-O2", f"-I{vroot}/include", f"-I{vroot}/include/vltstd", f"-I{w / 'ref'}", f"-I{w / 'dut'}",
        str(TB), *map(str, libs), f"{vroot}/include/verilated.cpp", f"{vroot}/include/verilated_threads.cpp", "-pthread",
        "-o", str(exe)], w / "link.log")
    p = subprocess.run([str(exe), f"+seeds={a.seeds}", f"+seed0={a.seed0}", f"+ops={a.ops}"], capture_output=True, text=True)
    out = p.stdout + p.stderr
    (w / "run.log").write_text(out)
    print(out[-4000:], end="", flush=True)
    print(f"sp_pq_lockstep: mutant={a.mut or 'none'} rc={p.returncode}", flush=True)
    return p.returncode


if __name__ == "__main__":
    sys.exit(main())
