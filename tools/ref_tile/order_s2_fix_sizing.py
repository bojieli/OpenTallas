#!/usr/bin/env python3
"""Sizing ONLY: preserve standard source-bound fleet flow but stop before CTS/GRT."""
import json
from pathlib import Path
import pre_route_gate as P
P.REMOTE_SH=P.REMOTE_SH.replace('if [ "{TRIAL}" = 1 ]; then','if false; then')
g=P.Gate(); k=P.ROOT/'physical/ref_tile/qkd_hr_core_order_s2'; s=P.RT.load_spec(str(k/'spec.json'))
P.remote(g,k,s,'auto',0,24,False)
g.print()
p=P.ROOT/'results/arch/kv_order_s2_fix_1019/sizing_receipt.json';p.parent.mkdir(parents=True,exist_ok=True)
p.write_text(json.dumps({'scope':'synthesis_floorplan_only_no_CTS_no_GRT_no_gate_adoption','items':g.items,'source_binding':getattr(g,'source_binding',None)},indent=2)+'\n')
