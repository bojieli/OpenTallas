#!/usr/bin/env python3
"""Provisional centred entry for current VQ placement census; no CTS/signoff authority."""
import hashlib,json,sys
from pathlib import Path
out=Path(sys.argv[1]);out.mkdir(parents=True,exist_ok=True)
s=dict(schema='opentallas.master_plan_slice.v1',kind='core',die='s81',type='ot_s81sl_vq',module='ot_s81sl_vq',master_plan_sha256=hashlib.sha256(b'codex-vq-centred-placement-census-1028').hexdigest(),frozen=False,outline_um=[172.8,129.6],instances=[],keepouts=[],bays=[],entry_pins=[dict(name='core_clock',pin='clk',layer='M5',xy_um=[86.4,64.8])],islands=[],latency=dict(common_clock_latency_ps={'TT':250.0,'FF':202.5},tol_ps=40),core_clock_port='clk',gates={'geometry':'PASS','tree':'NOT RUN'},note='Placement-census candidate only. Structured tree follows real current-RTL sink census; no CTS, route, or signoff permitted from this slice.')
(out/'ot_s81sl_vq.json').write_text(json.dumps(s,indent=2)+'\n')
