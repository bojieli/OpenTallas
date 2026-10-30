"""Die-local physical station constructor: preserve each planned window and enforce its slot count.

The old global unconstrained path can place22regs as1/3/3/1/1/2/1/10 across8slots;
R3 correctly rejects995um/1reg. Solve each actual slot between its fixed windows,
reserving half the same reach for each boundary hop. Added stations are explicit.
"""
import math
import numpy as np
import station_resite as SR
import hub_repack as HR
import lane_add as L

def anchored_route(f,a,b,n,reach,boundary):
 nx,ny=f.shape;xx=np.arange(nx)[:,None]*SR.G;yy=np.arange(ny)[None,:]*SR.G
 da=abs(xx-a[0])+abs(yy-a[1]);db=abs(xx-b[0])+abs(yy-b[1]);reached=f&(da<=boundary+1e-6);layers=[reached]
 end=None
 for k in range(1,n+1):
  if k==n:
   cand=reached&(db<=boundary+1e-6)
   if cand.any():end=tuple(int(x)for x in np.unravel_index(np.where(cand,db,1e20).argmin(),f.shape))
   break
  reached=f&SR._dilate(reached,int(reach//SR.G));layers.append(reached)
 if end is None:return None
 rev=[end];cur=end
 for k in range(n-2,-1,-1):
  cx,cy=cur[0]*SR.G,cur[1]*SR.G;good=layers[k]&(abs(xx-cx)+abs(yy-cy)<=reach+1e-6)
  for q in rev:good[q]=False
  if not good.any():return None
  tx=a[0]+(b[0]-a[0])*(k+1)/(n+1);ty=a[1]+(b[1]-a[1])*(k+1)/(n+1);cost=abs(xx-tx)+abs(yy-ty)
  cur=tuple(int(x)for x in np.unravel_index(np.where(good,cost,1e20).argmin(),f.shape));rev.append(cur)
 regs=[(round(i*SR.G,4),round(j*SR.G,4))for i,j in rev[::-1]]
 pts=[a]+regs+[b]
 assert max(abs(x[0]-y[0])+abs(x[1]-y[1])for x,y in zip(pts,pts[1:]))<=reach+1e-5
 return regs

def install(B):
 cache={};B.anchored_diagnostics=[]
 def resite(chain,slots,start,end):
  out=[];rows=[]
  for sl in slots:
   p=sl[0];t=B.P.ptype(p)
   if p not in cache:
    rects=SR.core_rects(t);cache[p]=HR.Raster(*t['outline_um'],[x[1:]for x in rects]).f
   fi,wi=L.OPP[sl[2]],sl[3];fo,wo=sl[5],sl[6]
   ai=B.face_pt(B.P,p,fi,wi);bi=B.face_pt(B.P,p,fo,wo)
   a=B.P.to_type(p,ai);b=B.P.to_type(p,bi);found=None
   base=max(sl[8],math.ceil(sl[10]/B.smax))
   for n in range(base,base+4):
    rr=anchored_route(cache[p],a,b,n,B.reach,B.reach/2.)
    if rr is not None:found=rr;break
   if found is None:
    B.anchored_diagnostics.append(dict(part=p,reason='no_per_slot_path',old_count=sl[8],attempted_to=base+3,reach=B.reach));return None
   out.append([B.P.to_die(p,r)for r in found]);rows.append(dict(part=p,old_count=sl[8],new_count=len(found),added=len(found)-sl[8],route_um=sl[10]))
  pts=[start]+[r for rr in out for r in rr]+[end]
  worst=max(abs(x[0]-y[0])+abs(x[1]-y[1])for x,y in zip(pts,pts[1:]))
  assert worst<=B.reach+1e-5
  assert all(not B.macro_hits(sl[0],rr)for sl,rr in zip(slots,out))
  B.anchored_diagnostics.append(dict(result='constructed',slots=rows,worst_hop_um=worst,added_stations=sum(x['added']for x in rows)))
  return out
 B.resite=resite
