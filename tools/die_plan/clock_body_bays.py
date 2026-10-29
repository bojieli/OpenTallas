#!/usr/bin/env python3
"""Opt-in PREBUILD clock-body packing, not a gate or default plan change.
Outputs a frozen placement overlay and explicit per-port pad sites.
Caller must apply, reprice and render before physical work.
ASAP7 BUFx24 native body=1.62x0.27um; .54um R0 row pitch.
"""
import argparse,collections,json,math,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import schema
from die_trial import SiteMap
ap=argparse.ArgumentParser(description=__doc__)
ap.add_argument('plan');ap.add_argument('tree');ap.add_argument('--pads');ap.add_argument('--out',required=True)
ap.add_argument('--width',type=float,default=1.62);ap.add_argument('--height',type=float,default=.27)
ap.add_argument('--halo',type=float,default=2.16);ap.add_argument('--max-displacement',type=float,default=8.64)
a=ap.parse_args();R=Path(a.out);R.mkdir(parents=True,exist_ok=True)
P=schema.Plan(json.load(open(a.plan)));S=SiteMap(P,halo=a.halo);T=json.load(open(a.tree));counts=json.load(open(a.pads))['pad'] if a.pads else {}
assert all(k in {t['port'] for t in T['taps']} and isinstance(n,int) and n>=0 for k,n in counts.items()),'pad keys/counts must match actual tree'
W,H=a.width,a.height;DX,DY=.054,.54;OCC=collections.defaultdict(list);B=8.64;partidx=collections.defaultdict(list)
for k,r in enumerate(S.parts):
 for i in range(int(r[0]//250),int(r[2]//250)+1):
  for j in range(int(r[1]//250),int(r[3]//250)+1):partidx[i,j].append(k)
def buckets(b):
 for i in range(math.floor(b[0]/B),math.floor((b[2]-1e-8)/B)+1):
  for j in range(math.floor(b[1]/B),math.floor((b[3]-1e-8)/B)+1):yield i,j
def ov(a,b):return a[0]<b[2]-1e-8 and b[0]<a[2]-1e-8 and a[1]<b[3]-1e-8 and b[1]<a[3]-1e-8
def legal(q):
 x,y=q;b=(x,y,x+W,y+H)
 if not any(a[0]+.5<=x and b[2]<=a[2]-.5 and a[1]+.5<=y and b[3]<=a[3]-.5 for a in (S.parts[k] for k in partidx[int((x+W/2)//250),int((y+H/2)//250)])):return False
 ks=set()
 for i in range(math.floor(x/250),math.floor(b[2]/250)+1):
  for j in range(math.floor(y/250),math.floor(b[3]/250)+1):ks.update(S.idx.get((i,j),[]))
 if any(ov(b,S.forb[k]) for k in ks):return False
 return not any(ov(b,bb) for z in buckets(b) for _,bb in OCC[z])
def insert(n,q):
 b=(q[0],q[1],q[0]+W,q[1]+H)
 for z in buckets(b):OCC[z].append((n,b))
# One extra placement site between neighbours; preserve R0 rail orientation by using every other270nm row.
shifts=sorted([(31*i,j) for i in range(-5,6) for j in range(-16,17)],key=lambda z:(abs(z[0]*DX)+abs(z[1]*DY),abs(z[1]),z))
def take(name,p,anchor=None):
 x=round(p[0]/DX)*DX;y=round(p[1]/DY)*DY
 for di,dj in shifts:
  q=(round(x+di*DX,6),round(y+dj*DY,6))
  if anchor and abs(q[0]-anchor[0])+abs(q[1]-anchor[1])>a.max_displacement+1e-6:continue
  if legal(q):insert(name,q);return list(q)
 raise RuntimeError('no legal 8.64um body bay for '+name+' at '+str(p))
base={};moves=[]
for n,p in T['sites'].items():
 q=take(n,p,p);base[n]=q
 if abs(q[0]-p[0])+abs(q[1]-p[1])>1e-6:moves.append(dict(cell=n,old=p,new=q,manhattan_um=abs(q[0]-p[0])+abs(q[1]-p[1])))
if (T.get('meta') or {}).get('physical_dme') and moves:
 raise RuntimeError('physical DME homes are frozen; re-plan/reprice before changing '+str(len(moves))+' clock cells')
pads={}
for t in T['taps']:
 n=counts.get(t['port'],0)
 if not n:continue
 anchor=base['b'+str(t['node'])];last=anchor;p=[]
 for i in range(n):last=take(t['port']+'#'+str(i),last,anchor);p.append(last)
 pads[t['port']]=p
out=dict(pad=counts,sites=pads);json.dump(out,open(R/'tap_pad_bays.json','w'),indent=1);json.dump(dict(sites=base,scope='PREBUILD row/site/body/macro-halo legalisation; original point-only placement retained',moves=moves),open(R/'base_body_sites.json','w'),indent=1)
rep=dict(base_cells=len(base),pad_cells=sum(counts.values()),body_um=[W,H],site_pitch_um=DX,row_pitch_used_um=DY,macro_halo_um=a.halo,body_overlaps=0,macro_hits=0,unhosted=0,base_moved=len(moves),max_base_move_um=max((x['manhattan_um'] for x in moves),default=0.),max_pad_chain_hop_um=max((abs(p[i][0]-(p[i-1] if i else base['b'+str(t['node'])])[0])+abs(p[i][1]-(p[i-1] if i else base['b'+str(t['node'])])[1]) for t in T['taps'] if (p:=pads.get(t['port'])) for i in range(len(p))),default=0.))
rep['input_exact_coincident_extra']=sum(n-1 for n in collections.Counter(tuple(v) for v in T['sites'].values()).values());json.dump(rep,open(R/'bay_report.json','w'),indent=2);print(json.dumps(rep,indent=2))
