#!/usr/bin/env python3
"""Actual full37word V16 fanout/seat gate, no new copy-check requirement."""
import argparse,json,hashlib
from pathlib import Path
import w2_station_rb_gate as G
ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=False)
G.RELREG=True;G.SAFEV=True;G.PHASE_SEAT=True
cases=[]
for stage,dist,red in ((0,1,1),(0,1,0),(1,0,1),(1,0,0)):
 tag=f'bank37_s{stage}_d{dist}_r{red}'
 r=G.bank_bench(a.out,tag,stage,dist,red=red);cases.append(dict(name=tag,expect='pass',result=r));assert r['passed'],cases[-1]
for mutant in ('B1_live_q_no_alignment','B4_red_data_not_delayed'):
 r=G.bank_bench(a.out,mutant,0,1,mutant=mutant,red=1);cases.append(dict(name=mutant,expect='fail',result=r));assert r['compile_exit']==0 and r.get('runtime_exit') not in (0,124),cases[-1]
record=dict(schema='opentallas.w2-v16-bank-gate.v1',verdict='PASS',cases=cases,new_phase_copy_check=False,source_sha256={p:hashlib.sha256((G.ROOT/p).read_bytes()).hexdigest() for p in (G.BANK,'tools/w2_phase_seat_v16_gate.py')})
(a.out/'terminal.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record),flush=True)
