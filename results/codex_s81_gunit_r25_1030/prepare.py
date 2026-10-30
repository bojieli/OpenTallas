#!/usr/bin/env python3
"""Prepare ONLY intended R25 unit_i0 source/plan +1; no adoption or full-die proof."""
import argparse,copy,hashlib,json,re,subprocess,sys
from pathlib import Path
ap=argparse.ArgumentParser();ap.add_argument('plan');ap.add_argument('bound_wrapper');ap.add_argument('out');ap.add_argument('--tools',required=True);a=ap.parse_args()
R=Path(a.out).resolve();R.mkdir(parents=True,exist_ok=True);K=R/'kit';K.mkdir(exist_ok=True)
p=json.loads(Path(a.plan).read_bytes());original=copy.deepcopy(p);lane='unit__seqhost__gunit';ln=next(x for x in p['lanes']if x['id']==lane)
assert ln.get('fixed_cycles',0)==0,ln
sys.path.insert(0,a.tools);import schema
oldP=schema.Plan(copy.deepcopy(p));before={k:oldP.lane_latency(k) for k in oldP.lanes};assert before[lane]['cycles']==72
ln['fixed_cycles']=1;newP=schema.Plan(p);after={k:newP.lane_latency(k) for k in newP.lanes}
changed=[k for k in before if before[k]!=after[k]];assert changed==[lane],changed;assert after[lane]['cycles']==73
probe=copy.deepcopy(p);next(v for v in probe['lanes']if v['id']==lane).pop('fixed_cycles');assert probe==original,'unrelated plan values changed'
(R/'plan_candidate.json').write_text(json.dumps(p))
t=p['partition_types']['gunit__t1'];bus=copy.deepcopy(next(b for b in t['buses']if b['name']=='unit_i0'));assert bus['width']==267
text=Path(a.bound_wrapper).read_text();assert 'u_ist_unit_i0_'not in text
m=re.search(r'ot_dp_st #\(\.W\((\d+)\)\) u_bin_unit_i0 ',text);assert m and int(m[1])==265
bus['width']=265
entries=[e for e in t['internal_stations']if e['conn']=='bus:unit_i0'];assert len(entries)==1 and entries[0]['regs_um']==[[1440.08,328.32]]
station={'partition_types':{'gunit__t1':{'outline_um':t['outline_um'],'buses':[bus],'internal_stations':entries}}}
(R/'station_plan_native265.json').write_text(json.dumps(station,indent=2))
f=K/Path(a.bound_wrapper).name;f.write_text(text);(R/'original.sv').write_text(text)
(K/'kit_rtl.json').write_text(json.dumps({'bound_module':f.stem,'files':[str(f)]}))
subprocess.run([sys.executable,str(Path(a.tools)/'kit_istations.py'),str(R/'station_plan_native265.json'),'gunit__t1',str(K),'--apply'],check=True)
c=f.read_text();assert len(re.findall(r'ot_dp_st #\(\.W\(265\)\) u_ist_unit_i0_0 ',c))==1
for e in ['.cw_a(unit_i0_is0_q[7:0])','.cw_d(unit_i0_is0_q[263:8])','.cw_v(unit_i0_is0_q[264])']:assert e in c,e
c=re.sub(r'(input\s+wire\s+\[265:0\] unit_i0,\s*//[^\n]*)72 cycles',r'\g<1>73 cycles',c);f.write_text(c)
receipt=dict(scope='PRIVATE_CANDIDATE_NOT_ADOPTED',r25_event='117e37566c',source_plan_sha256=hashlib.sha256(Path(a.plan).read_bytes()).hexdigest(),bound_wrapper_sha256=hashlib.sha256(text.encode()).hexdigest(),candidate_sha256=hashlib.sha256(c.encode()).hexdigest(),lane=lane,old=before[lane],candidate=after[lane],changed_lanes=changed,canonical_payload_capacity=267,actual_payload=265,epoch_bits=1,logical_added_flops=266,full_mapped_count='NOT RUN',canonical_other_plan_values_unchanged=True,unresolved=['current parent2spareinput ABI reconciliation','actualCW perbit placement and reset/clock admission','complete programme/calendar exposure','full parent/BoundDie proof and eventfreeze approval'])
(R/'receipt.json').write_text(json.dumps(receipt,indent=2))
print(json.dumps(receipt,indent=2))
