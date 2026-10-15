"""Actual LEF/TT first-load pin constraints for bounded geometry exploration."""
import json,gzip
from pathlib import Path
import numpy as np
from screen_compressed_tile import load_pins,xy

class PinConstraints:
 def __init__(self,inventory,pairs,views,parent_repo,boundaries):
  pairpath=Path(pairs);self.pairs=json.loads(gzip.decompress(pairpath.read_bytes())if pairpath.suffix=='.gz'else pairpath.read_text());self.by={};self.pins={};self.costs={p.stem:json.loads(p.read_text())['corners']['tt']for p in Path(boundaries).glob('*.json')};D=json.loads(Path(inventory).read_text())
  for r in self.pairs:
   for n in {r['source'][0],r['sink'][0]}:self.by.setdefault(n,[]).append(r)
  for b in D['children']+D['data_banks']+D['reset_nodes']:
   m=b['master']
   if m not in self.pins:
    p=Path(parent_repo)/b['view']/(m+'.lef')if b.get('kind')=='child'else Path(views)/m/'views'/m/(m+'.lef');self.pins[m]=load_pins(p,b['w'],b['h'])
 def arc(self,b,p,role):
  c=self.costs[b['master']];v=c['pins'].get(p,{}).get('O_minus_R_ps'if role=='o'else'S_plus_R_ps')
  return None if v is None else(v,c['R_ps'],c['clock_extrema_packet_ps']['launch'if role=='o'else'capture'])
 def filter(self,options,placed):
  if not options:return []
  fixed={b['inst']:b for b in placed};groups={}
  for score,q in options:groups.setdefault((q['master'],q.get('orient','R0')),[]).append((score,q))
  keep=[]
  for _,opts in groups.items():
   q=opts[0][1];name=q['inst'];local=[];other=[];bounds=[]
   zero={**q,'x':0,'y':0}
   for r in self.by.get(name,[]):
    if r['source'][0]==r['sink'][0]:continue
    ownsource=r['source'][0]==name;_,p=r['source']if ownsource else r['sink'];n,t=r['sink']if ownsource else r['source']
    if n not in fixed:continue
    b=fixed[n];a=self.arc(q,p,'o'if ownsource else's');c=self.arc(b,t,'s'if ownsource else'o')
    if a is None or c is None:continue
    maximum=(833.333-60-(150 if max(a[1],c[1])>300 else 90)-a[0]-c[0]-a[2]-c[2]-15)/.76
    local.append(xy(zero,self.pins[q['master']][p]));other.append(xy(b,self.pins[b['master']][t]));bounds.append(maximum)
   if not bounds:keep+=opts;continue
   local=np.asarray(local);other=np.asarray(other);bounds=np.asarray(bounds)
   # Batch options to bound memory even for full-shape pinned buses.
   for start in range(0,len(opts),64):
    batch=opts[start:start+64];origins=np.asarray([[v['x'],v['y']]for _,v in batch]);length=np.abs(origins[:,None,:]+local[None,:,:]-other[None,:,:]).sum(axis=2);valid=np.all(length<=bounds[None,:]+1e-6,axis=1);keep.extend(v for v,ok in zip(batch,valid)if ok)
  return keep
