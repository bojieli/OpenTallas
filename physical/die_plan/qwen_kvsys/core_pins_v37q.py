#!/usr/bin/env python3
"""KV-P7-V38 10-23: top-down core pins for the v3.7q core sites.  Same tool as core_pins_v37p.py (faces / orients chosen
from the bound partition netlist partners at the CURRENT core sites), but with its v3.7p layout moves switched off:
post_v37q.py owns the sites (the kvs_pc serpentine and the pv row order are already in them).
usage: core_pins_v37q.py die_plan_v37q.json RTL_DIR OUT_PLAN_DIR   (RTL_DIR = binder3 kv39 rtl/)"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'tools/die_plan'))
import core_pins_v37p as CP  # noqa: E402
import check as C            # noqa: E402
import schema as S           # noqa: E402

CP.apply_layout = lambda types: {}
CP.C = C
CP.SP = S.Plan(json.load(open(sys.argv[1])))
CP.main()
