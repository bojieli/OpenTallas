#!/usr/bin/env python3
"""Held source-current native-shape home candidates; actual pin centres only.
Partial parent grants and remaining soft logic are explicit. No cut/closure claim.
"""
import argparse,collections,gzip,json,math,re,sys
from pathlib import Path
import numpy as np

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--inputs',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--render',action='store_true');ap.add_argument('--case',choices=['row4','square4','read_mid'],required=True);a=ap.parse_args();R=a.inputs;a.out.mkdir(parents=True,exist_ok=True)
 leaves=json.loads((R/'native_pins/leaves.json').read_text())['leaves']
 with gzip.open(R/'native_pins/models.json.gz','rt')as f:models=json.load(f)
 base=json.loads((R/'baseline.json').read_text());grant=json.loads((R/'parent_pins.json').read_text());W,H=grant['outline_um'];N=len(leaves);dims=np.array([l['outline_um']for l in leaves]);pose=np.zeros((N,4));ids={l['path']:i for i,l in enumerate(leaves)};old={k.replace('dut.u_core.u_ws.a2f','dut.u_core.u_mem.u_front'):v for k,v in base['placement'].items()};known=set();aliases={}
 for i,l in enumerate(leaves):
  p=l['path'];q=p
  if p=='dut.u_core.u_mem.u_front.u_header':q='dut.u_core.u_ws.u_header'
  mm=re.fullmatch(r'dut.u_core.u_land.u_lane([0-3])',p)
  if mm:q='dut.u_core.u_land.lane'+mm[1]
  if p=='dut.u_core.u_land.u_fault':q='dut.u_core.u_land.fault_join'
  if q in old:v=old[q];pose[i]=[v[1],v[2],v[5],v[6]];known.add(i);aliases[p]=q
  mm=re.fullmatch(r'dut.u_core.u_mem.u_front.payload\[(\d)\].u_payload.quarter\[(\d)\].u_leaf',p)
  if mm:
   s,q=map(int,mm.groups());v=base['placement'][f'dut.u_core.u_ws.w0_payload[{s}].u_payload'];x,y=v[1:3]
   if a.case=='square4':x+=(q%2)*313.2;y+=(q//2)*54.0-10.8
   else:x+=q*313.2;y+=(32.4 if v[6]else 0)
   pose[i]=[x,y,v[5],v[6]];known.add(i)
 movable={i for i,l in enumerate(leaves)if i not in known or l['path'] in base['placement']and '.u_core.'not in l['path']and base['placement'][l['path']][2]==1760.4 and base['placement'][l['path']][4]==345.6}
 if a.case=='read_mid':movable|={i for i,l in enumerate(leaves)if re.search(r'\.d(?:4[89]|5\d|6[0-3])$',l['path'])}
 for i in set(range(N))-known:pose[i]=[W/2,H/2,0,0]
 def lp(i,p,b):
  l=leaves[i];ps=models[l['pin_source']]['pins'];n=p+f'[{b}]'if l['ports'][p]['bits']>1 else p
  if n not in ps:n=p+'[0]'
  return ps[n]['anchor_um']
 def parent(p,b):
  if p not in grant['ports']:return None
  g=grant['ports'][p];face,layer,c,depth=g['per_bit'][b];return {'W':(depth/2,c),'E':(W-depth/2,c),'N':(c,H-depth/2),'S':(c,depth/2)}[face]
 edges=[];unassigned=collections.Counter();live_soft=collections.Counter();bundles=collections.Counter()
 with gzip.open(R/'graph/pin_join.jsonl.gz','rt')as f:
  for line in f:
   n=json.loads(line)
   if n['status']=='CONSTANT':continue
   ds=n['drivers'];cs=n['consumers']
   for i,p,b,d in cs:
    if i<0:continue
    for j,q,c,dd in ds:
     if j>=0:
      if i==j:continue
      xy=lp(i,p,b);uv=lp(j,q,c);edges.append((i,xy[0],xy[1],j,uv[0],uv[1]));bundles[(j,i)]+=1
     elif j==-1:
      uv=parent(q,c)
      if uv is None:unassigned[q]+=1;continue
      xy=lp(i,p,b);edges.append((i,xy[0],xy[1],-1,uv[0],uv[1]))
     else:live_soft[(j,i,p)]+=1
   for j,q,c,dd in ds:
    if j<0:continue
    for i,p,b,d in cs:
     if i!=-1:continue
     uv=parent(p,b)
     if uv is None:unassigned[p]+=1;continue
     xy=lp(j,q,c);edges.append((j,xy[0],xy[1],-1,uv[0],uv[1]))
 E=np.array(edges);adj=collections.defaultdict(list)
 for i,x,y,j,u,v in edges:
  adj[i].append((x,y,j,u,v))
  if j>=0:adj[j].append((u,v,i,x,y))
 def points(i):
  z=np.array(adj[i]);others=z[:,2].astype(int);px=z[:,3].copy();py=z[:,4].copy();mask=others>=0;ii=others[mask];px[mask]=pose[ii,0]+np.where(pose[ii,2]>0,dims[ii,0]-px[mask],px[mask]);py[mask]=pose[ii,1]+np.where(pose[ii,3]>0,dims[ii,1]-py[mask],py[mask]);return z[:,:2],px,py
 def cost1(xs,targets):
  ts=np.sort(targets);pre=np.r_[0,np.cumsum(ts)];n=np.searchsorted(ts,xs);return xs*(2*n-len(ts))+pre[-1]-2*pre[n]
 def place(i,occupied):
  w,h=dims[i];own,px,py=points(i);obs=np.array([[pose[j,0],pose[j,1],*dims[j]]for j in occupied]);gap=21.6
  xs=np.r_[np.arange(gap,W-w-gap+1e-5,86.4),obs[:,0]-w-gap,obs[:,0]+obs[:,2]+gap,pose[i,0]];ys=np.r_[np.arange(gap,H-h-gap+1e-5,86.4),obs[:,1]-h-gap,obs[:,1]+obs[:,3]+gap,pose[i,1]]
  xs=np.unique(np.round(xs[(xs>=gap-1e-5)&(xs+w<=W-gap+1e-5)],5));ys=np.unique(np.round(ys[(ys>=gap-1e-5)&(ys+h<=H-gap+1e-5)],5));legal=np.ones((len(xs),len(ys)),dtype=bool)
  for x,y,ww,hh in obs:legal&=~((xs[:,None]<x+ww+gap-1e-5)&(xs[:,None]+w+gap>x+1e-5)&(ys[None,:]<y+hh+gap-1e-5)&(ys[None,:]+h+gap>y+1e-5))
  if not legal.any():raise RuntimeError('no native-shape slot '+leaves[i]['path'])
  best=None
  for fx,fy in [(0,0),(1,0),(0,1),(1,1)]:
   lx=w-own[:,0]if fx else own[:,0];ly=h-own[:,1]if fy else own[:,1];cost=cost1(xs,px-lx)[:,None]+cost1(ys,py-ly)[None,:];cost[~legal]=np.inf;k=np.unravel_index(np.argmin(cost),cost.shape);v=(float(cost[k]),float(xs[k[0]]),float(ys[k[1]]),fx,fy)
   if best is None or v<best:best=v
  pose[i]=best[1:]
 fixed=set(range(N))-movable;order=sorted(movable,key=lambda i:(-np.prod(dims[i]),leaves[i]['path']));placed=set(fixed)
 for i in order:place(i,placed);placed.add(i)
 for turn in range(2):
  for i in order:place(i,set(range(N))-{i})
  print('PLACED',a.case,'pass',turn,flush=True)
 def absxy(ii,x,y):
  ii=ii.astype(int);ok=ii>=0;xx=x.copy();yy=y.copy();j=ii[ok];xx[ok]=pose[j,0]+np.where(pose[j,2]>0,dims[j,0]-xx[ok],xx[ok]);yy[ok]=pose[j,1]+np.where(pose[j,3]>0,dims[j,1]-yy[ok],yy[ok]);return xx,yy
 x,y=absxy(E[:,0],E[:,1],E[:,2]);u,v=absxy(E[:,3],E[:,4],E[:,5]);dist=np.abs(x-u)+np.abs(y-v);inside=E[:,3]>=0
 overlap=[]
 for i in range(N):
  for j in range(i):
   if min(pose[i,0]+dims[i,0],pose[j,0]+dims[j,0])-max(pose[i,0],pose[j,0])>1e-5 and min(pose[i,1]+dims[i,1],pose[j,1]+dims[j,1])-max(pose[i,1],pose[j,1])>1e-5:overlap.append([leaves[i]['path'],leaves[j]['path']])
 out=dict(schema='opentallas.s81.actual-current-home-screen.v1',case=a.case,status='HELD_SCREEN_NOT_ADOPTED',outline_um=[W,H],leaves=N,selected_graph='5dd27586d actual534-leaf XML f95528d...; future536 capture split NOT added',macro_overlaps=overlap,all_incident_scope='All direct hard-to-hard bit edges plus exact capture/MIX4 parent pins; constants local; remaining live soft operators and missing parent grants explicit, not routable.',bit_edges=len(edges),internal_bit_edges=int(inside.sum()),internal_star_bit_um=float(dist[inside].sum()),internal_max_um=float(dist[inside].max()),internal_p99_um=float(np.quantile(dist[inside],.99)),internal_edges_over_400um=int((dist[inside]>400).sum()),hop_scope='400um screen threshold only; native per-leaf launch/capture and real route/relay cycles still required, no generic reach grant.',unassigned_parent_consumers=dict(unassigned),unhomed_soft_incident_bits=sum(live_soft.values()),movable=len(movable),normal_cycle_delta=0,root_delta=0,placement={l['path']:dict(master=l['master'],kit=l['kit'],x_um=float(pose[i,0]),y_um=float(pose[i,1]),w_um=float(dims[i,0]),h_um=float(dims[i,1]),flip_x=bool(pose[i,2]),flip_y=bool(pose[i,3]),pin_model=l['pin_source'])for i,l in enumerate(leaves)},not_claimed=['Full parent/die cut <=0.60','Unassigned parent pins and clock/reset phi-R delivery','Native qualification from geometry','Fixed compiler cost or source adoption','Physical home for remaining soft operator nodes'])
 (a.out/(a.case+'.json')).write_text(json.dumps(out,indent=1)+'\n')
 if not a.render:
  print('DONE',a.case,out['internal_star_bit_um'],out['internal_max_um'],out['internal_p99_um'],'overlaps',len(overlap),flush=True);return
 import matplotlib;matplotlib.use('Agg');import matplotlib.pyplot as plt
 from matplotlib.patches import Rectangle
 from matplotlib.collections import LineCollection
 def color(m):
  if m=='dsfd_vm_static_bank128':return '#d2deea'
  if 'payload33'in m:return '#a580bf'
  if 'field4'in m:return '#a4bdac'
  if 'read_q'in m or 'return_bank'in m:return '#7ab0ca'
  if 'wfc'in m or 'xio'in m:return '#ef9176'
  if 'fault'in m or 'diag'in m:return '#e4c96f'
  return '#cccccc'
 fig,ax=plt.subplots(figsize=(15,13));segments=[];widths=[]
 for (j,i),bits in bundles.items():
  if i not in movable and j not in movable:continue
  # Bundle display only: centres of actual per-bit endpoint sets, no routing anchor substitution.
  rows=np.where((E[:,0]==i)&(E[:,3]==j)|(E[:,0]==j)&(E[:,3]==i))[0]
  if not len(rows):continue
  segments.append([(float(x[rows].mean()),float(y[rows].mean())),(float(u[rows].mean()),float(v[rows].mean()))]);widths.append(min(1.2,.15+bits/1500))
 ax.add_collection(LineCollection(segments,linewidths=widths,colors='#333333',alpha=.12))
 for i,l in enumerate(leaves):
  xx,yy=pose[i,:2];ww,hh=dims[i];ax.add_patch(Rectangle((xx,yy),ww,hh,facecolor=color(l['master']),edgecolor='#555555',linewidth=.25))
  if i in movable and ('xio'in l['master']or'wfc'in l['master']):ax.text(xx+ww/2,yy+hh/2,l['path'].removeprefix('dut.').replace('u_',''),fontsize=4,ha='center',va='center')
 ax.set(xlim=(0,W),ylim=(0,H),aspect='equal',xlabel='VM-local x (um)',ylabel='VM-local y (um)',title=f'{a.case}: actual534-leaf held home screen\nActual shapes/pins; missing parent grants and live soft operators prevent cut/closure adoption')
 fig.tight_layout();fig.savefig(a.out/(a.case+'.png'),dpi=150);ax.set_xlim(1900,5036.664);ax.set_ylim(1550,2350);fig.set_size_inches(17,6);fig.tight_layout();fig.savefig(a.out/(a.case+'_middle.png'),dpi=160);plt.close(fig)
 print('DONE',a.case,out['internal_star_bit_um'],out['internal_max_um'],out['internal_p99_um'],'overlaps',len(overlap),flush=True)
if __name__=='__main__':main()
