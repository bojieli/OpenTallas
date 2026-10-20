#!/usr/bin/env python3
"""Compare proposed PVJOIN pair envelopes with immutable actual GEN9 case.
Planning only: no source mutations, no physical/timing/age admission implied.
"""
import argparse,collections,hashlib,json,re
from pathlib import Path
ap=argparse.ArgumentParser();ap.add_argument('--case',required=True);ap.add_argument('--out',required=True);a=ap.parse_args();b=Path(a.case);out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
lef=(b/'elements.lef').read_text();sizes={}
for z in re.finditer(r'(?m)^MACRO (\S+)\s*$(.*?)(?=^MACRO |\Z)',lef,re.S|re.M):
 m=re.search(r'\bSIZE\s+([\d.]+)\s+BY\s+([\d.]+)',z[2]);
 if m:sizes[z[1]]=list(map(float,m.groups()))
insts={m[2]:m[1] for m in re.finditer(r'(?m)^\s*(\w+)\s+(\w+)\s*\(', (b/'die.v').read_text()) if m[1]!='module'}
placed={}
for z in re.finditer(r'findInst (\S+)\] ([\d.]+) ([\d.]+) (\w+)',(b/'place.tcl').read_text()):
 n,x,y,o=z.groups();master=insts.get(n);assert master in sizes,(n,master);w,h=sizes[master];placed[n]=dict(name=n,master=master,xy=[float(x),float(y)],wh=[w,h],orient=o)

def rect(p):
 x,y=p['xy'];w,h=p['wh'];return x,y,x+w,y+h
def ov(p,q):
 x,y,xx,yy=rect(p);a,b,aa,bb=rect(q);return min(xx,aa)-max(x,a),min(yy,bb)-max(y,b)
grps={n:p for n,p in placed.items() if n.startswith('slg_')};assert len(grps)==32
report=dict(scope='MODEL ONLY: native leaf outline changes do not qualify parent pins/relay ages/reach. Actual pre-expand GEN9 frames are not native leaf widths.',inputs={n:sha(b/n) for n in ['die.v','elements.lef','place.tcl','manifest.json']},parent_source='75171867d gen9d9q immutable pre-expand snapshot',die_um=json.load(open(b/'manifest.json'))['die_um'],baseline=grps,native_candidate_um=[388.8,432],leaf_area_growth_vs388_8square_um2=32*388.8*43.2,leaf_area_growth_vs388_8square_mm2=32*388.8*43.2/1e6,variants={})
for policy in ['preserve_inner_face','preserve_outer_face','centre']:
 cand={};details={};allpairs=set();funcpairs=set()
 for n,p in grps.items():
  west=n.split('_')[1][0]=='W';x,y=p['xy'];w,h=p['wh'];dw=388.8-w
  if policy=='preserve_inner_face':x-=dw if west else 0
  elif policy=='preserve_outer_face':x-=0 if west else dw
  else:x-=dw/2
  q=dict(p,xy=[round(x,6),round(y+(h-432)/2,6)],wh=[388.8,432]);cand[n]=q;hits=[]
  for nn,v in placed.items():
   if nn==n:continue
   dx,dy=ov(q,v)
   if dx<=1e-6 or dy<=1e-6:continue
   odx,ody=ov(p,v);old=odx>1e-6 and ody>1e-6
   row=dict(name=nn,master=v['master'],overlap_um=[round(dx,6),round(dy,6)],preexisting=old,xy=v['xy'],wh=v['wh']);hits.append(row)
   if not old:
    pair=tuple(sorted([n,nn]));allpairs.add(pair)
    if not v['master'].startswith(('qkd_rly','qkd_rst','qkd_fwd')):funcpairs.add(pair)
  details[n]=dict(candidate=q,width_deficit_old_frame_um=round(dw,6),oldframe_vertical_surplus_um=round(h-432,6),collisions=hits,new_functional_collisions=[v for v in hits if not v['preexisting'] and not v['master'].startswith(('qkd_rly','qkd_rst','qkd_fwd'))])
 report['variants'][policy]=dict(new_pair_collisions=len(allpairs),new_functional_pair_collisions=len(funcpairs),new_functional_pairs=sorted(funcpairs),instances=details)
(out/'grp_parent_fit.json').write_text(json.dumps(report,indent=1)+'\n');print(json.dumps({k:{t:v[t] for t in ['new_pair_collisions','new_functional_pair_collisions','new_functional_pairs']} for k,v in report['variants'].items()},indent=1))
