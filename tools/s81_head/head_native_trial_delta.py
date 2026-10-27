#!/usr/bin/env python3
"""Compose HEAD trial core geometry from its own native abstracts; no signoff claim."""
import argparse,hashlib,json,re
from pathlib import Path

def pins(path):
 text=path.read_text(); out=[]
 for name,body in re.findall(r'^\s*PIN\s+(\S+)\n(.*?)^\s*END\s+\1\s*$',text,re.M|re.S):
  r=re.search(r'LAYER\s+(M\d+)\s*;\s*RECT\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)',body)
  if not r: raise ValueError('no native rectangle '+name)
  l,*v=r.groups(); x0,y0,x1,y1=map(float,v)
  out.append(dict(name=name,layer=l,x=round((x0+x1)/2,6),y=round((y0+y1)/2,6)))
 size=re.search(r'SIZE\s+([\d.]+)\s+BY\s+([\d.]+)',text)
 return list(map(float,size.groups())),out

def apply(plan,lefs,pdir):
 report=[]; t=plan['partition_types']['hd_tile']
 for mod,path in lefs.items():
  size,ps=pins(path); clk=[p for p in ps if p['name']=='ft_mstrap_i']
  if len(clk)!=1: raise ValueError('native clock ambiguous '+mod)
  xy=[clk[0]['x'],clk[0]['y']]
  for h in t['hard_cores']:
   if h['module']!=mod: continue
   old=list(h['outline_um']); h['outline_um']=size
   h['track_offset_um']=[0,0]
   ts=[v for v in t['clock']['taps'] if v['name'].startswith(h['inst']+'.')]
   if len(ts)!=1: raise ValueError('tap count '+h['inst'])
   x,y=xy; o=h.get('orient','R0')
   if o in ('MY','R180'): x=size[0]-x
   if o in ('MX','R180'): y=size[1]-y
   ts[0]['name']=h['inst']+'.ft_mstrap_i'; ts[0]['xy']=[round(h['origin_um'][0]+x,6),round(h['origin_um'][1]+y,6)]
   ts[0]['note']='Native R16 trial geometry; insertion budget pending this view signoff; no early tap.'
   h['note']='R16 native abstract trial; size/pins from this own-view LEF; timing remains unsigned until signoff.py SIGNED plus routed LEC.'
   pf=pdir/h['pins_file']; pf.parent.mkdir(parents=True,exist_ok=True)
   pf.write_text(json.dumps(dict(source=str(path),source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),macro=mod,outline_um=size,pins=ps,status='UNSIGNED_TRIAL'),indent=1)+'\n')
   report.append(dict(inst=h['inst'],old_outline=old,new_outline=size,clock_native=xy,tap=ts[0]['xy'],pins=len(ps)))
 return report

def main():
 a=argparse.ArgumentParser(); a.add_argument('plan',type=Path); a.add_argument('--a',type=Path,required=True); a.add_argument('--b',type=Path,required=True); a.add_argument('--out',type=Path,required=True); o=a.parse_args()
 p=json.loads(o.plan.read_text()); report=apply(p,{'ot_s81hd_elemA_cv':o.a,'ot_s81hd_elemB_cv':o.b},o.out.parent)
 o.out.write_text(json.dumps(p,indent=2)+'\n'); print(json.dumps(report,indent=1))
if __name__=='__main__': main()
