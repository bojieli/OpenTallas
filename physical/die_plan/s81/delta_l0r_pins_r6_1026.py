#!/usr/bin/env python3
"""S81-CORE-LAT-R6 2026-10-26 (COORD RULING 15:12 gunit_l0r): PLAN pin re-assignment of dsdv_gunit_l0r.

delta_l0r_refit_1025 grew the l0r outline 172.8 -> 267.84 um and re-spread the W-face pin table with xfin_pins(), whose
block-shift of bus groups stacked 321 of 737 pins on 146 sites (the l0r groups wr_bd / r_d / wr_ad interleave bit by bit),
which aborted the r3rt22 kit's GRT (GRT-0080, 255 GRT-0031 stacked M4 W-face pins).  This delta regenerates the table from
the pre-refit plan table (git 77523b3ce^, 172.8-um outline, 0 stacked) with the fixed xfin_pins() (interleaved faces are
re-spread pin by pin, order + 0.192 pitch kept) and then runs tools/die_plan/core_pin_sites_gate.py on it (fail closed).
Outline, origin, faces and pin layers are unchanged; only W-face y positions move.  usage: python3 -I delta_l0r_pins_r6_1026.py
"""
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(HERE))
from delta_cconn_1025 import xfin_pins  # noqa: E402

PRE = "77523b3ce^"
PF = HERE / "inputs/core_pins/dsdv_gunit_l0r.json"
src = subprocess.run(["git", "-C", str(REPO), "show", f"{PRE}:physical/die_plan/s81/inputs/core_pins/dsdv_gunit_l0r.json"],
                     check=True, capture_output=True, text=True).stdout
PF.write_text(src)
assert xfin_pins(PF, (267.84, 267.84), old_outline=172.8)
d = json.loads(PF.read_text())
d["source"] = d["source"].replace("bus groups re-spread along each face",
                                  "bus groups re-spread along each face; S81-CORE-LAT-R6 10-26: interleaved W-face groups "
                                  "re-spread pin by pin (order + 0.192 pitch kept, 0 stacked; core_pin_sites_gate PASS)")
PF.write_text(json.dumps(d, indent=1) + "\n" if src.startswith("{\n") else json.dumps(d) + "\n")
r = subprocess.run([sys.executable, "-I", str(REPO / "tools/die_plan/core_pin_sites_gate.py"), "--pins", str(PF),
                    "--outline", "267.84", "267.84"])
sys.exit(r.returncode)
