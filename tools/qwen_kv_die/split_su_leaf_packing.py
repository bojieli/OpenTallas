#!/usr/bin/env python3
"""Actual-leaf SU lane packing and exact bit-pin seam audit; excludes reducer/glue."""
import gzip,hashlib,json,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/hier_contract'))
import pair_check as P
OUT=ROOT/'results/arch/qwen_split_feasibility_1013'
table=P.load_table(OUT/'su_closed_timing.json')
masters=json.loads((OUT/'su_closed_masters.json').read_text())
leaves={}
for master,view in masters.items():
 p=ROOT/view/(master+'.lef');s=p.read_text();w,h=map(float,re.search(r'SIZE\s+(\S+)\s+BY\s+(\S+)',s).groups());pins={}
 for m in re.finditer(r'^\s*PIN\s+(\S+)\s*$(.*?)^\s*END\s+\1\s*$',s,re.M|re.S):
  q=re.search(r'LAYER\s+(\S+)\s*;\s*RECT\s+([-\d. ]+)\s*;',m[2]);
  if q:
   x0,y0,x1,y1=map(float,q[2].split());pins[m[1]]=[(x0+x1)/2,(y0+y1)/2,q[1]]
 leaves[master]=dict(w=w,h=h,pins=pins,lef_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),view_source_hashes={str(f.relative_to(ROOT)):hashlib.sha256(f.read_bytes()).hexdigest() for f in (ROOT/view).iterdir() if f.is_file() and (f.suffix in ('.lib','.lef') or f.name=='insertion.json')})
H='ot_hdc_vstream_lane_h'; E='ot_hdc_sfu_exp_t';R='ot_hdc_sfu_rcp_t';Q='ot_hdc_sfu_rsq_t'
# A complete lane cluster has four closed views in the existing wires-only RTL.
rel={H:(108.,0.),E:(0.,151.2),R:(151.2,151.2),Q:(280.8,151.2)}
rects=[]
for row in range(8):
 for col in range(8):
  for master,(x,y) in rel.items():
   leaf=leaves[master];rects.append(dict(name=f'l{row*8+col}_{master}',master=master,x=x+col*432.0,y=y+row*324.0,w=leaf['w'],h=leaf['h']))
overlap=[]
for j,p in enumerate(rects):
 for q in rects[j+1:]:
  if p['x']<q['x']+q['w']-1e-6 and q['x']<p['x']+p['w']-1e-6 and p['y']<q['y']+q['h']-1e-6 and q['y']<p['y']+p['h']-1e-6:overlap.append([p['name'],q['name']])
die=P.Die(table,{})
seams=[];missing=[]
for s,pre in [(E,'exp'),(R,'rcp'),(Q,'rsq')]:
 for a,ap,b,bp,n in [(H,'sx_'+pre+'_x',s,'x',32),(H,'sx_'+pre+'_v',s,'v',1),(s,'y',H,'sy_'+pre+'_y',32),(s,'fault',H,'sy_'+pre+'_f',1)]+([(s,'vo',H,'sy_exp_vo',1)] if pre=='exp' else []):
  for bit in range(n):
   pa=ap+f'[{bit}]' if n>1 else ap;pb=bp+f'[{bit}]' if n>1 else bp
   if pa not in leaves[a]['pins'] or pb not in leaves[b]['pins']:missing.append([a,pa,b,pb]);continue
   ax,ay,_=leaves[a]['pins'][pa];bx,by,_=leaves[b]['pins'][pb]
   length=abs(ax+rel[a][0]-bx-rel[b][0])+abs(ay+rel[a][1]-by-rel[b][1])
   verdict=P.check(die,dict(a=('a',a,pa),b=('b',b,pb),um=length))
   seams.append(dict(a=[a,pa],b=[b,pb],um=round(length,6),timing_833ps_sensitivity=verdict))
summary=dict(status='REAL_LEAF_COMPONENT_ONLY_NO_FULL_SU_FIT',lane_count=64,closed_children=256,
 outline_um=[8*432.0-21.6,8*324.0-21.6],child_area_mm2=sum(p['w']*p['h'] for p in rects)/1e6,
 overlaps=overlap,unique_seam_bits=len(seams),total_repeated_seam_bits=len(seams)*64,
 max_bit_um=max(s['um'] for s in seams),over_500_bits=sum(s['um']>500 for s in seams),missing_pin_pairs=missing,
 timing_sensitivity_status_counts={k:sum(s['timing_833ps_sensitivity']['status']==k for s in seams) for k in ('pass','fail','hold')},
 leaves={k:{x:y for x,y in v.items() if x!='pins'} for k,v in leaves.items()},positions=rects,seams=seams,
 missing=['88,388-flop reducer, common glue, queue/control and full native x3 formatter are absent.',
 'Exact entire SU64 native mapping to this hard lane cluster remains unimplemented; these four-leaf lanes are existing source components.',
 'Boundary VM/cbuf/crom/instruction/reduction seams, tracks and relay equalization are not included.',
 'Timing is per-pair 833ps sensitivity using actual TT/FF ETM and insertion; actual serial1111ps domain and physical phi-R clock delivery must be bound.',
 'Full-parent PG, routed wire/cut proof, SS internal constraints and native cycle benchmark remain required.'])
gzip.open(OUT/'su_lane_component_packing.json.gz','wt').write(json.dumps(summary)+'\n')
print(json.dumps({k:v for k,v in summary.items() if k not in ('positions','seams','leaves','missing')},indent=2))
