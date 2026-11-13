#!/usr/bin/env python3
"""HARD-QC-FORMS-1 form F-STA-RTL: verilog define OT_QC_SWREG on every QC type whose bound RTL instantiates
qfd_dv_s8_station_tail1 regions (st_a x9; st_b when its RTL carries u_scale_wait).  usage: form_sta.py PLAN FORM_OUT.json [TYPE_REGEX]"""
import json, sys, re
P = json.load(open(sys.argv[1])); pt = P["partition_types"]; rx = re.compile(sys.argv[3] if len(sys.argv) > 3 else r"^sl[ew]_st_a_")
ops = [{"op": "add_define", "type": t, "define": "OT_QC_SWREG"} for t in sorted(pt) if rx.search(t)]
json.dump({"name": "F-STA-RTL scale_wait output register (HARD-QC-FORMS-1 11-13)", "ops": ops}, open(sys.argv[2], "w"), indent=1); print("ops", len(ops))
