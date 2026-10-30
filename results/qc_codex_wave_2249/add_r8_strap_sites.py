#!/usr/bin/env python3
"""Materialize already-bound R8 count straps as physical pins; retain all existing sites."""
import argparse,copy,json,re,sys
from pathlib import Path

def apply(raw,manifest,kits,repo,plan_path):
 sys.path.insert(0,str(Path(repo)/'tools/die_plan'))
 import schema as S,gen_phys as G
 out=copy.deepcopy(raw); report={}
 for kr in kits:
  tn=kr['plan_type']; bt=kr['bound_type']; t=out['partition_types'][tn]
  bop={p['port']:(p['dir'],int(p['width'])) for p in kr['bound_only_pins']}
  want={n:int(v['width']) for n,v in manifest['types'].get(bt,{}).items() if v.get('kind')=='r8pad_strap'}
  bound={n:w for n,(d,w) in bop.items() if n.startswith('strap_r8pad_') and d=='input'}
  if want!=bound:raise ValueError(f'{tn}: manifest and bound-only R8 ports differ: {want} vs {bound}')
  if not want:continue
  for q in kr['instances']:
   for n,w in want.items():
    v=manifest['instances'][q][n]
    if v.get('kind')!='r8pad_strap' or v['width']!=w or not 0<=v['value']<2**w:raise ValueError(f'{tn}.{q}.{n}: bad tied contract')
  cs=t.setdefault('count_straps',[]); old={s['name']:s for s in cs}; new=[]
  for n,w in sorted(want.items()):
   if n in old:
    if old[n]['width']!=w or len(old[n].get('sites_um',[]))!=w:raise ValueError(f'{tn}.{n}: bad existing contract')
    continue
   s=dict(name=n,width=w,note='OWNER 10-28 R8 pad-count strap; bind parent manifest, unchanged values/cycles');cs.append(s);new.append(s)
  if not new:continue
  P=S.Plan(out,path=plan_path);w,h=t['outline_um'];blocked=[]
  for inst,mod,lef,lib,x,y,ori in G.type_macros(P,tn):
   text=(Path(repo)/lef).read_text();m=re.search(r'\bSIZE\s+([\d.]+)\s+BY\s+([\d.]+)\s*;',text)
   if not m:raise ValueError(f'{tn}: no actual LEF size {lef}')
   mw,mh=map(float,m.groups())
   if ori in ('R90','R270','E','W','FE','FW','MXR90','MYR90'):mw,mh=mh,mw
   blocked.append((x-5.4,y-5.4,x+mw+5.4,y+mh+5.4))
  for r in t.get('clock',{}).get('reserved_sites_um',[]):
   a,b,c,d=r['rect_um'];blocked.append((a-1.08,b-1.08,c+1.08,d+1.08))
  occupied=[(p['x'],p['y']) for p in G.plan_pin_records(P,tn,G.type_pins(P,tn))]
  ax,ay=t.get('clock',{}).get('tap_um',[w/2,h/2]);cand=[]
  for ix in range(2,int(w/4.32)-1):
   x=round(ix*4.32,4)
   for iy in range(2,int(h/4.32)-1):
    y=round(iy*4.32,4)
    if any(a<=x<=c and b<=y<=d for a,b,c,d in blocked):continue
    cand.append((abs(x-ax)+abs(y-ay),x,y))
  cand.sort();needed=sum(s['width'] for s in new);sites=[]
  for _,x,y in cand:
   if any(abs(x-a)<2.16 and abs(y-b)<2.16 for a,b in occupied):continue
   sites.append([x,y]);occupied.append((x,y))
   if len(sites)==needed:break
  if len(sites)!=needed:raise ValueError(f'{tn}: no physical room for {needed} R8 pins')
  cur=0
  for s in new:s['layer']='M5';s['sites_um']=sites[cur:cur+s['width']];cur+=s['width']
  report[tn]=dict(new_bits=needed,ports={s['name']:s['width'] for s in new},layer='M5',added_cycles=0,source_instances=kr['instances'])
 errors=S.validate(out)
 if errors:raise ValueError(errors[:10])
 return out,report

def main():
 p=argparse.ArgumentParser();p.add_argument('plan',type=Path);p.add_argument('manifest',type=Path);p.add_argument('kits',type=Path);p.add_argument('--repo',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 out,rep=apply(json.loads(a.plan.read_text()),json.loads(a.manifest.read_text()),[json.loads(k.read_text()) for k in sorted(a.kits.glob('*/kit_rtl.json'))],a.repo,a.plan)
 a.out.write_text(json.dumps(out,indent=1)+'\n');a.out.with_suffix('.r8_sites.json').write_text(json.dumps(rep,indent=1)+'\n');print(json.dumps(rep))
if __name__=='__main__':main()
