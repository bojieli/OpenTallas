#!/usr/bin/env python3
"""Screen a source-exact full-width transport candidate for five NE bank7 outputs.
No source adoption: the full DMA return/request timing bundle must be materialized.
Current source supports II1, so serial_k=2 cannot carry arbitrary legal responses.
"""
import sys,json,copy
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[3]/'tools/die_plan'))
import plan_cut as C
p=Path(sys.argv[1]);r=json.load(open(p/'die_plan.json'));tn='q_hub_ne';t=r['partition_types'][tn];old=copy.deepcopy(t)
widths={'eg':276,'pr':266,'status':18,'xq_done':1,'xq2_done':1};changes=[]
for s in t['internal_stations']:
 name=s.get('launch','').removeprefix('u_vmb_Q7.')
 if not s.get('launch','').startswith('u_vmb_Q7.') or name not in widths or s.get('capture')!='u_hb_vms_Q':continue
 w=widths[name];assert len(s['regs_um'])==6,(name,len(s['regs_um']))
 changes.append(dict(conn=s['conn'],old_bits=s['bits'],old_parallel=s.get('bits_parallel'),source_bits=w,stages=6,extra_cycles_vs_actual_direct=6))
 s['bits']=w;s.pop('bits_parallel',None);s.pop('serial_k',None);s.pop('r11_cc_serial',None)
 s['native_source_bits']=w;s['note']+=' | CODEX actual-source full-width candidate: II1 preserved, no serializer/epoch, not adopted'
assert len(changes)==5,len(changes)
W,H=t['outline_um']
def screen(q):return C._cut_profile(W,H,C._nets(q),C._cores(q),per_sink=True)
report=dict(schema='hbm.native_fullwidth.v1',qualification='LOWER_BOUND_SCREEN_ONLY',changes=changes,added_flops=sum(6*(x['source_bits']-x['old_bits']) for x in changes),before=screen(old),after=screen(t),source_gate='PREP: source materialization and complete per-bank request/return dates required',physical_gate='NOT RUN: per-bit station bays/geometry, PG, clock, route, timing')
out=Path(sys.argv[2]);out.mkdir(parents=True,exist_ok=True)
(out/'fullwidth_report.json').write_text(json.dumps(report,indent=1));(out/'die_plan.json').write_text(json.dumps(r,indent=1))
print(json.dumps(report,indent=1))
