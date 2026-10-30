#!/usr/bin/env python3
"""A-only fine-grid conditional relay model: actual obstacles and endpoint coordinates; conditional on later per-bit FIRM.
Interior hops<=300um; end hops<=180um. A future40um-L1 per-bit allocation plus30um pin reach and<=151.2um
endpoint pin halfspan would bound those wire hops under405um (180+151.2+30+40=401.2). This is not that allocation or a physical gate.
"""
import sys,json,math
from pathlib import Path
import numpy as np
from scipy.ndimage import distance_transform_cdt
sys.path.insert(0,sys.argv[1]+'/tools/die_plan')
import schema as S
raw=json.load(open(sys.argv[2]));lots=json.load(open(sys.argv[3]))['proposals'];G=4.32;END=180.;MID=300.;HALO=4.32
allrows=[];merges=[]
def solve(free,a,b):
 X,Y=np.meshgrid(np.arange(free.shape[0])*G+.702,np.arange(free.shape[1])*G+.135,indexing='ij')
 near=lambda p:np.abs(X-p[0])+np.abs(Y-p[1])
 first=free&(near(a)<=END);last=free&(near(b)<=END)
 if not first.any() or not last.any():return dict(verdict='NO_FIRST_OR_LAST_GROUP_SPACE',first_points=int(first.sum()),last_points=int(last.sum()))
 layers=[first];q=first&last
 for n in range(1,100):
  if q.any():break
  d=distance_transform_cdt(~layers[-1],metric='taxicab')
  f=free&(d*G<=MID+1e-6)
  if np.array_equal(f,layers[-1]):return dict(verdict='COARSE_COMPONENT_DISCONNECTED')
  layers.append(f);q=f&last
 else:return dict(verdict='COARSE_99_STAGE_SEARCH_EXHAUSTED')
 n=len(layers);ideal=np.array(a)+(np.array(b)-np.array(a))*n/(n+1)
 ix=np.unravel_index(np.argmin(np.where(q,near(ideal),np.inf)),free.shape);p=np.array(ix)*G+np.array([.702,.135]);path=[p.tolist()]
 for j in range(n-2,-1,-1):
  ok=layers[j]&(near(p)<=MID+1e-6);ideal=np.array(a)+(np.array(b)-np.array(a))*(j+1)/(n+1)
  ix=np.unravel_index(np.argmin(np.where(ok,near(ideal),np.inf)),free.shape);p=np.array(ix)*G+np.array([.702,.135]);path.append(p.tolist())
 path.reverse();chain=[a]+path+[b];hops=[sum(abs(x-y) for x,y in zip(u,v)) for u,v in zip(chain,chain[1:])]
 return dict(verdict='CENTRE_PATH_ONLY',relay_groups=n,points_um=path,max_centre_hop_um=max(hops),first_um=hops[0],last_um=hops[-1])
for part in ['NW_hub','NE_hub']:
 pp=next(p for p in raw['partitions'] if p['name']==part);t=raw['partition_types'][pp['type']];W,H=t['outline_um']
 X,Y=np.meshgrid(np.arange(math.ceil(W/G))*G+.702,np.arange(math.ceil(H/G))*G+.135,indexing='ij');free=(X>HALO)&(X<W-HALO)&(Y>HALO)&(Y<H-HALO)
 def block(a,b,c,d):
  nonlocal_dummy=0
  i,j=max(0,math.floor(a/G)),max(0,math.floor(b/G));ii,jj=min(free.shape[0],math.ceil(c/G)+1),min(free.shape[1],math.ceil(d/G)+1);free[i:ii,j:jj]=False
 for a,b,c,d in S.placed_macro_boxes(t,halo=HALO).values():block(a,b,c,d)
 for s in t.get('internal_stations',[]):
  R=4.32+math.sqrt(max(1,s.get('bits',1))*.5832/2)
  for x,y in s.get('regs_um',[]):block(x-R,y-R,x+R,y+R)
 for s in t.get('ft_slots',[]):
  for st in s.get('bit_sites_um',[]):
   for x,y in st:block(x,y,x+1.404,y+.27)
  if not s.get('bit_sites_um'):
   R=4.32+math.sqrt((s['width']+1)*.5832/2)
   for x,y in s.get('regs_um',[]):block(x-R,y-R,x+R,y+R)
 ll=sorted([p for p in lots if p['part']==part and p['verdict']=='ESTIMATE_SPACE_ONLY'],key=lambda p:int(p['raw'][-1]))
 for p in ll:
  x,y=p['origin_um'];block(x-HALO,y-HALO,x+302.4+HALO,y+151.2+HALO)
 def nearest(z):
  d=np.abs(X-z[0])+np.abs(Y-z[1]);ix=np.unravel_index(np.argmin(np.where(free,d,np.inf)),free.shape);return [float(X[ix]),float(Y[ix])]
 cp=next(h for h in t['hard_cores'] if h['inst']=='u_hb_dbk_Q__q1');cp_ep=[cp['origin_um'][0]+cp['outline_um'][0],cp['origin_um'][1]+cp['outline_um'][1]/2]
 for g in range(2):
  q=ll[g*4:g*4+4];ns=[[p['origin_um'][0]+151.2,p['origin_um'][1]+151.2] for p in q];m=nearest(np.median(ns,axis=0));merges.append(dict(part=part,quartet=g,centre_um=m))
  for p,n in zip(q,ns):
   x,y=p['origin_um'];rx,ry=p['raw_origin_um']
   for family,width,a,b in [('fill_tap_extension',560,[rx+71.28,ry],[x+151.2,y]),('LOADcmd',63,cp_ep,[x+302.4,y+75.6]),('packet_to_quartet',281,n,m)]:
    row=dict(part=part,source_leaf=p['raw'],family=family,width_bits=width,a_um=a,b_um=b,manhattan_um=sum(abs(v-u) for u,v in zip(a,b)),result=solve(free,a,b));allrows.append(row);print(json.dumps({k:v for k,v in row.items() if k!='result'}|{'result':{k:v for k,v in row['result'].items() if k!='points_um'}}),flush=True)
  for bank in [h for h in t['hard_cores'] if h['inst'].startswith('u_vmb_Q')]:
   ep=[bank['origin_um'][0]+135,bank['origin_um'][1]]
   allrows.append(dict(part=part,quartet=g,family='local_bank_delivery',width_bits=281,bank=bank['inst'],a_um=m,b_um=ep,result=solve(free,m,ep)))
result=dict(scope=__doc__,grid_um=G,endpoint_bound_um=END,interior_bound_um=MID,group_L1_radius_assumed_um=40,actual_PIN_allocation_not_done=True,clock='same logical PLLstream0/833ps; physical F4,reset,START and PG remain open',mergers=merges,links=allrows)
Path(sys.argv[4]).write_text(json.dumps(result,indent=1)+'\n')
