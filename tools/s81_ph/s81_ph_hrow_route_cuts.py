#!/usr/bin/env python3
"""Construct explicit grid-edge A* routes with normal escapes from actual face pins.

Capacities are M2-M7 at80% usable, with onlyM6 horizontal and85%M7 vertical
above M5 tiles. Each route group retains its actual endpoint pins; no endpoint
cell is erased. Escape demand is counted on the first grid edge outside the
macro. This is routing geometry evidence, not extracted RC or timing closure.
"""
import numpy as np
import gzip, json, hashlib, subprocess, tempfile
from pathlib import Path
G=10.8;WIN=5;USABLE=.8
HF=7/.270/2+1/.048+1/.064;VF=1/.036/2+1/.048+.85/.064
HL=1/.064;VL=.85/.064

def check(plan,w,h,chunk=8,passes=16,dump_path=None,wire_limit_um=None):
 nx,ny=int(np.ceil(w/G)),int(np.ceil(h/G));capH=np.full((ny,nx-1),HF*G*USABLE);capV=np.full((ny-1,nx),VF*G*USABLE)
 rects=plan.rects()
 for name,(x0,y0,x1,y1,master) in rects.items():
  for ix in range(max(0,int(x0//G)),min(nx-1,int(np.ceil(x1/G)))):
   cut=(ix+1)*G
   if x0+1e-6<cut<x1-1e-6:
    for iy in range(max(0,int(y0//G)),min(ny,int(np.ceil(y1/G)))):
     span=max(0,min(y1,(iy+1)*G)-max(y0,iy*G));capH[iy,ix]-=(HF-HL)*span*USABLE
  for iy in range(max(0,int(y0//G)),min(ny-1,int(np.ceil(y1/G)))):
   cut=(iy+1)*G
   if y0+1e-6<cut<y1-1e-6:
    for ix in range(max(0,int(x0//G)),min(nx,int(np.ceil(x1/G)))):
     span=max(0,min(x1,(ix+1)*G)-max(x0,ix*G));capV[iy,ix]-=(VF-VL)*span*USABLE
 if (capH<=0).any() or (capV<=0).any():raise ValueError('Overlapping macros yield invalid cut capacity; fix placement first')
 useH=np.zeros_like(capH);useV=np.zeros_like(capV)
 def cell(p,n):
  x,y,face,layer=p;x0,y0,x1,y1,_=rects[n]
  # Pin-to-normal escape reaches the first free gcell centre outside the own tile.
  if face=='W':ix=int(np.floor(x0/G-.5));iy=int(y//G)
  elif face=='E':ix=int(np.ceil(x1/G-.5));iy=int(y//G)
  elif face=='S':ix=int(x//G);iy=int(np.floor(y0/G-.5))
  else:ix=int(x//G);iy=int(np.ceil(y1/G-.5))
  return min(max(ix,0),nx-1),min(max(iy,0),ny-1)
 def path(a,b,mid,kind):
  ax,ay=a;bx,by=b;out=[]
  def H(y,a,b):out.extend((0,y,x) for x in range(min(a,b),max(a,b)))
  def V(x,a,b):out.extend((1,y,x) for y in range(min(a,b),max(a,b)))
  if kind==0:
   if mid is None:H(ay,ax,bx);V(bx,ay,by)
   else:V(ax,ay,mid);H(mid,ax,bx);V(bx,mid,by)
  else:
   if mid is None:V(ax,ay,by);H(by,ax,bx)
   else:H(ay,ax,mid);V(mid,ay,by);H(by,mid,bx)
  return list(dict.fromkeys(out))
 # Small neighbouring-bit groups avoid collapsing a wide pin footprint into one landing.
 segs=[]
 for ei,(cls,a,b,A,B) in enumerate(plan.hops):
  if cls=='reset_direct_rtl':continue
  for pt,name in [(q,a) for q in A]+[(q,b) for q in B]:
   landing=cell(pt,name);physical=(min(nx-1,max(0,int(pt[0]//G))),min(ny-1,max(0,int(pt[1]//G))))
   for dd,yy,xx in path(physical,landing,None,0):(useH if dd==0 else useV)[yy,xx]+=1
  for k in range(0,len(A),chunk):
   aa=[cell(q,a) for q in A[k:k+chunk]];bb=[cell(q,b) for q in B[k:k+chunk]]
   # Keep distinct endpoints: groups share a route only if both exact landing cells match.
   grouped={}
   for j,(q,r) in enumerate(zip(aa,bb)):
    grouped.setdefault((q,r),[]).append(dict(source_pin=plan.edges[ei]['source_pins'][k+j],sink_pin=plan.edges[ei]['sink_pins'][k+j],source_point_um=A[k+j][:2],sink_point_um=B[k+j][:2],actual_rc_budget_um=None))
   segs.extend((len(pairs),q,r,cls,a,b,A[k][2],B[k][2],pairs) for (q,r),pairs in grouped.items())
 escapeH,escapeV=useH.copy(),useV.copy()
 def window_sum(U,axis):return np.apply_along_axis(lambda a:np.convolve(a,np.ones(WIN),'valid'),axis,U)
 cWH,cWV=window_sum(capH,0),window_sum(capV,1)
 uWH,uWV=window_sum(useH,0),window_sum(useV,1)
 def prepared(route):
  a=np.asarray(route,dtype=int).reshape(-1,3);hh=a[a[:,0]==0,1:];vv=a[a[:,0]==1,1:]
  hwy=np.clip(hh[:,0,None]-np.arange(WIN),0,ny-WIN);vwx=np.clip(vv[:,1,None]-np.arange(WIN),0,nx-WIN)
  return hh,vv,hwy,vwx
 chosen=[None]*len(segs)
 def adjust(q,delta):
  hh,vv,*_=q
  for U,WU,ee,d in [(useH,uWH,hh,0),(useV,uWV,vv,1)]:
   if not len(ee):continue
   yy,xx=ee[:,0],ee[:,1];U[yy,xx]+=delta
   ww=(yy[:,None] if d==0 else xx[:,None])-np.arange(WIN);valid=(ww>=0)&(ww<(ny-WIN+1 if d==0 else nx-WIN+1))
   other=np.broadcast_to(xx[:,None] if d==0 else yy[:,None],ww.shape)
   np.add.at(WU,(ww[valid],other[valid]) if d==0 else (other[valid],ww[valid]),delta)
 source=Path(__file__).with_name('hrow_grid_router.cpp')
 executable=Path(tempfile.gettempdir())/'s81_hrow_grid_router'
 subprocess.run(['g++','-O3','-std=c++17',str(source),'-o',str(executable)],check=True)
 with tempfile.TemporaryDirectory(prefix='s81-hrow-routes-') as tmp:
  ip,op=Path(tmp)/'input',Path(tmp)/'output'
  faces={'E':0,'W':1,'N':2,'S':3}
  with ip.open('w') as f:
   f.write(f'{nx} {ny} {len(segs)}\n')
   for values in (capH,capV,useH,useV):np.savetxt(f,values.reshape(1,-1),fmt='%.12g')
   for bits,a,b,cls,src,dst,fa,fb,pairs in segs:
    escape=max(sum(abs(pp['source_point_um'][j]-(a[j]+.5)*G)+abs(pp['sink_point_um'][j]-(b[j]+.5)*G) for j in (0,1)) for pp in pairs)
    limit=int(np.floor((wire_limit_um-escape)/G+1e-10)) if wire_limit_um is not None else -1
    f.write(f'{bits} {a[0]} {a[1]} {b[0]} {b[1]} {faces[fa]} {faces[fb]} {limit}\n')
  subprocess.run([str(executable),str(ip),str(op)],check=True)
  lines=op.read_text().splitlines();assert int(lines[0])==len(segs)
  for i,line in enumerate(lines[1:]):
   v=list(map(int,line.split()));arr=np.asarray(v[1:],dtype=int).reshape(-1,3);assert len(arr)==v[0];chosen[i]=prepared(arr.tolist());adjust(chosen[i],segs[i][0])
 it=0
 def windows(U,C,axis):
  k=np.ones(WIN)
  A=np.apply_along_axis(lambda a:np.convolve(a,k,'valid'),axis,U);B=np.apply_along_axis(lambda a:np.convolve(a,k,'valid'),axis,C)
  R=A/B;pos=np.unravel_index(np.argmax(R),R.shape);return float(R[pos]),[int(v) for v in pos]
 wH,pH=windows(useH,capH,0);wV,pV=windows(useV,capV,1)
 fullH=useH.sum(axis=0)/capH.sum(axis=0);fullV=useV.sum(axis=1)/capV.sum(axis=1)
 if dump_path:
  path=Path(dump_path)
  if path.exists():
   history=path.parent/'history';history.mkdir(exist_ok=True);(history/(hashlib.sha256(path.read_bytes()).hexdigest()+'.routes.json.gz')).write_bytes(path.read_bytes())
  def document_route(s,q):
   grid_length=(len(q[0])+len(q[1]))*G
   pairs=[]
   for pp in s[8]:
    length=grid_length+sum(abs(pp['source_point_um'][i]-(s[1][i]+.5)*G)+abs(pp['sink_point_um'][i]-(s[2][i]+.5)*G) for i in (0,1))
    pairs.append(dict(pp,grid_polyline_um=round(length,4)))
   return dict(bits=s[0],source_cell=s[1],sink_cell=s[2],cls=s[3],source_instance=s[4],sink_instance=s[5],source_face=s[6],sink_face=s[7],H=q[0].tolist(),V=q[1].tolist(),exact_pairs=pairs)
  document=dict(schema='opentallas.hrow_concrete_grid_routes.v1',gcell_um=G,outline_um=[w,h],capacity_H=capH.tolist(),capacity_V=capV.tolist(),escape_demand_H=escapeH.tolist(),escape_demand_V=escapeV.tolist(),routes=[document_route(s,q) for s,q in zip(segs,chosen)])
  with gzip.open(path,'wt') as f:json.dump(document,f,separators=(',',':'))
 return dict(schema='opentallas.hrow_grid_edge_routes.v1',gcell_um=G,window_um=G*WIN,groups=len(segs),chunk_max_bits=chunk,passes='A* repeated rip-up; up to16',pin_normal_escape=True,capacity='M2-M7 only;80% usable;overM5 M6(H),85%M7(V)',physical_polyline_limit_um=wire_limit_um,full_vertical_cut_max=[round(float(fullH.max()),4),round(float((fullH.argmax()+1)*G),2)],full_horizontal_cut_max=[round(float(fullV.max()),4),round(float((fullV.argmax()+1)*G),2)],window_vertical_cut_max=round(wH,4),window_horizontal_cut_max=round(wV,4),window_vertical_worst_gcell=pH,window_horizontal_worst_gcell=pV,gcell_max=[round(float((useH/capH).max()),4),round(float((useV/capV).max()),4)],pass_=max(wH,wV,float(fullH.max()),float(fullV.max()))<=.6 and max(float((useH/capH).max()),float((useV/capV).max()))<=1.0,route_segments=sum(len(r[0])+len(r[1]) for r in chosen),grid_route_path_max_um=round(max(len(r[0])+len(r[1]) for r in chosen)*G,2))
