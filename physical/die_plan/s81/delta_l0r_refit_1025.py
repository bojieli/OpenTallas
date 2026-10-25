#!/usr/bin/env python3
"""Grow measured l0r boundary RTL to a 50-percent-fill lattice outline; no cycle change."""
import json
from pathlib import Path
import compact_plan
from delta_cconn_1025 import xfin_pins
HERE=Path(__file__).resolve().parent
p=HERE/"die_plan.json"
d=json.loads(p.read_text())
h=next(c for c in d["partition_types"]["gunit__t1"]["hard_cores"] if c["module"]=="dsdv_gunit_l0r")
if h["outline_um"] != [267.84,267.84]:
 old=h["outline_um"]
 if old != [172.8,172.8]: raise ValueError(f"unexpected old l0r outline {old}")
 h["outline_um"]=[267.84,267.84]
 xfin_pins(HERE/"inputs/core_pins/dsdv_gunit_l0r.json",(267.84,267.84),old_outline=old[0])
 p.write_text(compact_plan.dumps(d))
