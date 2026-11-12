#!/usr/bin/env python3
"""HEAD-94 11-11: hd_ctl setup form (COORD fail-watch hd_ctl 7d13b54a98b6, TT -88.05).
 Worst setup path: u_cland_lepk_i0/u_fault_port/q (clk_t15, arrival 449) -> u_cland_up_lepk_o0/fault_o (clk_t31, 410): 849 ps of
 status-fault collector (QN 91 + buf 118 + INV 75 + OR4 148 + OA21 41 + four placement buffers 280, two 27 fF wires).  One registered
 1-input status relay on the lepk_i0 -> lepk_o0 status leg (landing_status_input_stages, status observed one cycle later, 0 data cycles)
 splits it.  usage: ctl_form_event.py BASE_PLAN.json[.gz] OUT.json"""
import gzip, json, sys
from pathlib import Path
src = Path(sys.argv[1]); raw = gzip.open(src).read() if src.suffix == ".gz" else src.read_bytes()
P = json.loads(raw); c = P["partition_types"]["hd_ctl"]["clock"]
assert "landing_status_input_stages" not in c
c["landing_status_input_stages"] = {"lepk_o0": {"lepk_i0": [{"xy_um": [54.0, 265.0]}]}}
Path(sys.argv[2]).write_text(json.dumps(P, indent=1) + "\n")
