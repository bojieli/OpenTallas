#!/usr/bin/env python3
"""Source FF reservation, never synthesis/native area/fanout qualification."""
import hashlib,json,re
from pathlib import Path
W=Path(__file__).resolve().parents[2]
p=W/'rtl/hbm_accel/generic/adapters/static_su/reduction/ot_hbm_r6_station41.sv'
s=re.sub(r'//[^\n]*|/\*.*?\*/','',p.read_text(),flags=re.S).split('module ot_hbm_r6_add_node')[0]
assigned=set(re.findall(r'\b([a-zA-Z_]\w*)\s*(?:\[[^\]]+\])?\s*<=',s));regs=[]
for m in re.finditer(r'\breg\s*(?:\[(\d+)\s*:\s*(\d+)\])?\s*([^;]+);',s):
 width=abs(int(m[1])-int(m[2]))+1 if m[1] else 1
 for term in m[3].split(','):
  x=re.fullmatch(r'(\w+)(?:\[(\d+):(\d+)\])?',term.strip().split('=')[0].strip());assert x,term
  n=abs(int(x[2])-int(x[3]))+1 if x[2] else 1
  if x[1] in assigned:regs.append(dict(name=x[1],bits=width*n,source_offset=m.start()))
d=dict(method='Each lexical declaration with NBA assignment retained, including diagnostic state. Arithmetic reservation from unchanged source sizing571/node. No synthesized/native fanout/area/clock or SAFE claim.',source_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),top_clocked_bits=sum(r['bits']for r in regs),top_clocked_registers=len(regs),private_node_opr_bits=41*65,native_add_lat_reservation_bits=41*506,total_private_reservation_bits=sum(r['bits']for r in regs)+41*571,qcore_root_additional_bits=34,possible_constant_mode_ff_removal_reported_separately=41*7,final_root_capture_bits=33,former_minimum=51483+1200,registers=regs)
(W/'results/arch/hbm_record6_implement_1019/source_ff_reservation.json').write_text(json.dumps(d,indent=2)+'\n')
print(json.dumps({k:v for k,v in d.items()if k!='registers'}))
