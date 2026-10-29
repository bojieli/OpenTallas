#!/usr/bin/env python3
"""HEAD hk5 fix-only FT face stations; keep unrelated type geometry unchanged."""
import argparse,gzip,json,subprocess,sys
from pathlib import Path
ap=argparse.ArgumentParser();ap.add_argument('plan');ap.add_argument('out');a=ap.parse_args()
root=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(root/'tools/die_plan'))
import schema as S,gen_phys as G
src=Path(a.plan).resolve();out=Path(a.out).resolve();out.mkdir(parents=True,exist_ok=True)
raw=json.loads(gzip.open(src,"rt").read() if src.suffix==".gz" else src.read_text());P=S.Plan(raw,src)
types=['hd_st_k5','hd_st_m','hd_st_n3_transit','hd_st_n3_turn','hd_st_n4','hd_st_str','hd_st_turn','hd_turn_a','hd_turn_b']
for tn in types:
 d=out/'pins'/tn;d.mkdir(parents=True,exist_ok=True)
 ps=[dict(bus=b,bit=i,layer=l,x=x,y=y,face=f) for b,i,l,x,y,f in G.type_pins(P,tn)]
 (d/'pins.json').write_text(json.dumps(ps))
# Preserve relative-view meaning after moving the plan, so reset/source generation cannot follow a dangling copied symlink.
for t in raw['partition_types'].values():
 for c in t.get('hard_cores',[]):
  if c.get('pins_file') and not Path(c['pins_file']).is_absolute():c['pins_file']=str((src.parent/c['pins_file']).resolve())
base=out/'base.json';base.write_text(json.dumps(raw))
with (out/'stations.jsonl').open('w') as log:
 subprocess.run([sys.executable,str(Path(__file__).with_name('ftface.py')),str(base),str(out/'plan.json'),str(out/'pins'),'--mode','v1','--with-regs','--reach','364.5','--types',','.join(types)],check=True,stdout=log)
new=json.loads((out/'plan.json').read_text())
for tn in types:
 ck=new['partition_types'][tn]['clock'];ck['control_sinks']=True;ck['tap_radius_um']=150.
(out/'plan.json').write_text(json.dumps(new,indent=1)+'\n')
A=S.Plan(raw,base);B=S.Plan(new,out/'plan.json');diff=[]
for n in A.lanes:
 x=A.lane_latency(n)['cycles'];y=B.lane_latency(n)['cycles']
 if x!=y:diff.append(dict(lane=n,old=x,new=y,added=y-x))
(out/'latency_delta.json').write_text(json.dumps(diff,indent=1)+'\n')
print('types',len(types),'changed_lanes',len(diff),'added_cycles',sum(r['added'] for r in diff))

subprocess.run([sys.executable,str(root/'tools/die_plan/gen.py'),'latency',str(out/'plan.json'),'--out',str(out/'latency'),'--inplace'],check=True)
