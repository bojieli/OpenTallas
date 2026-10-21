#!/usr/bin/env python3
"""Congestion-aware macro-free source construction for regional72.

Actual G8 signals M2..M8; M9 clock/PG excluded. Cut budgets distinguish
horizontal M2/M4/M6/M8 and vertical M3/M5/M7 with exact current track pitches
and global-route adjustments. No window budget or anchor is physical closure.
"""
import argparse,collections,heapq,json,math
from pathlib import Path
import numpy as np

def main():
 ap=argparse.ArgumentParser();ap.add_argument('plan');ap.add_argument('out');ap.add_argument('--penalty',type=float,default=20.0);a=ap.parse_args();p=json.load(open(a.plan));bs=p['blocks'];W,H=p['facts']['die_um'];pad=43.2;stub=43.2
 # blocks plus geometry-only blockages (S81-LINKS gap reserves: no pins, never bound) are obstacles alike
 rect=[(b['x']-pad,b['y']-pad,b['x']+b['w']+pad,b['y']+b['h']+pad)for b in bs+p.get('blockages',[])]
 def outer(e,f):
  x,y=e[2:4];return(round(x+(-stub if f=='W'else stub if f=='E'else 0),4),round(y+(-stub if f=='S'else stub if f=='N'else 0),4))
 terms={l['i']:[outer(e,f)for e,f in zip(l['e'],l['endpoint_faces'])]for l in p['links']}
 xs=sorted({32.4,W-32.4}|{round(v,4)for r in rect for v in(r[0],r[2],(r[0]+r[2])/2)if 0<v<W}|{q[0]for t in terms.values()for q in t});ys=sorted({32.4,H-32.4}|{round(v,4)for r in rect for v in(r[1],r[3],(r[1]+r[3])/2)if 0<v<H}|{q[1]for t in terms.values()for q in t})
 nx,ny=len(xs),len(ys);xa,ya=np.array(xs),np.array(ys);blocked=np.zeros((ny,nx),dtype=np.bool_)
 for x0,y0,x1,y1 in rect:
  ix=np.flatnonzero((xa>x0+1e-5)&(xa<x1-1e-5));iy=np.flatnonzero((ya>y0+1e-5)&(ya<y1-1e-5))
  if len(ix)and len(iy):blocked[iy[0]:iy[-1]+1,ix[0]:ix[-1]+1]=True
 xi={x:i for i,x in enumerate(xs)};yi={y:i for i,y in enumerate(ys)}
 # Signal routing matches dv_rvcase.py G8 M2..M8, NOT legacy two-layer sum.
 # M4/M5 are available only in macro-free corridors; no over-block capacity.
 capacity={'V':260*(.5/.640+.7/.048+.8/.064+.8/.080),
           'H':260*(.5/.640+.7/.048+.8/.064)}
 usage=collections.Counter()
 def windows(a,b):
  x0,y0=a;x1,y1=b
  if y0==y1:
   return [('V',k,int(y0//260)) for k in range(int(min(x0,x1)//260)+1,int(math.ceil(max(x0,x1)/260)))]
  return [('H',k,int(x1//260)) for k in range(int(min(y0,y1)//260)+1,int(math.ceil(max(y0,y1)/260)))]
 # Cost caches belong to one link; committed usage does not change during it.
 def route(s,t,bits):
  start=(xi[s[0]],yi[s[1]]);goal=(xi[t[0]],yi[t[1]])
  if blocked[start[1],start[0]]or blocked[goal[1],goal[0]]:return None,'endpoint stub blocked'
  todo=[(abs(s[0]-t[0])+abs(s[1]-t[1]),0,start)];dist={start:0};prev={};edgecost={}
  while todo:
   _,g,u=heapq.heappop(todo)
   if g>dist.get(u,math.inf)+1e-6:continue
   if u==goal:
    path=[u]
    while u in prev:u=prev[u];path.append(u)
    return [(xs[x],ys[y])for x,y in path[::-1]],None
   x,y=u
   for xx,yy in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
    if xx<0 or yy<0 or xx>=nx or yy>=ny or blocked[yy,xx]:continue
    v=(xx,yy);ek=(min(u,v),max(u,v))
    if ek not in edgecost:
     length=abs(xs[xx]-xs[x])+abs(ys[yy]-ys[y])
     ws=windows((xs[x],ys[y]),(xs[xx],ys[yy]))
     pressure=max(((usage[w]+bits)/capacity[w[0]] for w in ws),default=0)
     edgecost[ek]=length*(1+a.penalty*(pressure/.60)**6)
    ng=g+edgecost[ek]
    if ng+1e-6>=dist.get(v,math.inf):continue
    dist[v]=ng;prev[v]=u;h=abs(xs[xx]-t[0])+abs(ys[yy]-t[1]);heapq.heappush(todo,(ng+h,ng,v))
  return None,'no macro-free path'
 failed=[];channels=[];stations=[]
 order=sorted(range(len(p['links'])),key=lambda i:(-p['links'][i]['b'],-sum(abs(terms[p['links'][i]['i']][0][j]-terms[p['links'][i]['i']][1][j]) for j in range(2)),p['links'][i]['i']))
 for count,i in enumerate(order):
  l=p['links'][i]
  q,err=route(*terms[l['i']],l['b'])
  if q is None:failed.append(dict(link=l['i'],reason=err));continue
  # Collapse grid collinear points. End stubs stay explicit for actual pin reprojection.
  pts=[tuple(l['e'][0][2:4])]+q+[tuple(l['e'][1][2:4])];clean=[]
  for q0 in pts:
   if clean and q0==clean[-1]:continue
   if len(clean)>1 and ((clean[-2][0]==clean[-1][0]==q0[0])or(clean[-2][1]==clean[-1][1]==q0[1])):clean[-1]=q0
   else:clean.append(q0)
  legs=[];length=0.;corners=[]
  for u,v in zip(clean,clean[1:]):
   ll=abs(v[0]-u[0])+abs(v[1]-u[1]);legs.append((length,length+ll,u,v));length+=ll;corners.append(length)
  n=max(1,math.ceil(length/350.));cuts=[]
  for k in range(1,n):
   t=k*length/n
   for c in corners[:-1]:
    if abs(t-c)<50:t=c-50 if t<=c else c+50
   cuts.append(t)
  def at(t):
   for lo,hi,u,v in legs:
    if t<=hi+1e-5:
     z=0 if hi==lo else(t-lo)/(hi-lo);return[u[0]+(v[0]-u[0])*z,u[1]+(v[1]-u[1])*z]
   return list(clean[-1])
  sp=[at(t)for t in cuts];marks=sorted(set([0.,length]+corners+cuts));hops=[]
  for lo,hi in zip(marks,marks[1:]):hops.append([*at(lo),*at(hi),l['b']])
  l.update(h=hops,sp=sp,s=len(sp),L=round(length,3));stations+=sp
  seen=set()
  for u,v in zip(clean,clean[1:]):seen.update(windows(u,v))
  for w in seen:usage[w]+=l['b']
  for u,v in zip(clean[1:-1],clean[2:-1]):channels.append([min(u[0],v[0])-16.2,min(u[1],v[1])-16.2,max(u[0],v[0])+16.2,max(u[1],v[1])+16.2])
  if count%25==0:print('ROUTE',count,'/',len(p['links']),'relay_stations',len(stations),flush=True)
 p['facts']['physical72'].update(routing='CONSTRUCTION_FAILED'if failed else'CONSTRUCTED_PENDING_REAL_PIN_PROJECTION_AND_SOURCE_GEN',routing_failures=failed,grid=[nx,ny],relay_station_count=len(stations),relay_cell_packing='PENDING exact master bodies/station collision legalization; no fictitious cell-site claim')
 p['facts']['physical72']['package_ports']=dict(placement_model='package bumps over/along actual existing interior PMA pin faces; no outer-shoreline path assumed',source_ports='retain all existing PMA external connections; actual kit/view pin manifest owed')
 p['facts'].update(relays=len(stations),bit_mm=sum(l.get('L',0)*l['b']for l in p['links'])/1000,relay_channels_seed=channels)
 p['facts']['physical72']['congestion_source_constructor']=dict(order='descending bus width then endpoint Manhattan distance',penalty=a.penalty,
  layers=dict(V=['M2 H .640 usable .50','M4 H .048 usable .70','M6 H .064 usable .80','M8 H .080 usable .80'],
              H=['M3 V .640 usable .50','M5 V .048 usable .70','M7 V .064 usable .80']),
  nominal_capacity_per_260um=capacity,
  layer_scope='Current G8 M2..M8 signals, M9 clock/PG excluded; exact track pitch and routing adjustment. Macro-free source graph. Actual macro/via/local routes/clock occupancy/GRT still owed; no mathematical mincut.',
  worst_nominal_directional_ratio=max((n/capacity[w[0]] for w,n in usage.items()),default=0),
  windows_over_060=sum(n/capacity[w[0]]>.60 for w,n in usage.items()),
  top_windows=[dict(direction=w[0],coordinate_um=w[1]*260,interval_um=[w[2]*260,(w[2]+1)*260],bits=n,nominal_tracks=capacity[w[0]],ratio=n/capacity[w[0]]) for w,n in sorted(usage.items(),key=lambda t:-t[1]/capacity[t[0][0]])[:20]])
 print('CONGESTION',json.dumps(p['facts']['physical72']['congestion_source_constructor']),flush=True)
 Path(a.out).write_text(json.dumps(p,indent=1));print('ROUTE_DONE failed',len(failed),'stations',len(stations),flush=True)
if __name__=='__main__':main()
