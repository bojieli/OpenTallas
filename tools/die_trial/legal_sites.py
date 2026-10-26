#!/usr/bin/env python3
"""Bulk nearest-physical-distance allocation on legal standard-cell rows.

Uniform footprints, sparse occupancy, rectangle keepouts. Coordinates are CELL
CENTRES in microns. Returns explicit sites; never changes bounds or relaxes the
maximum distance. Callers choose data-flow order and must review the result.
"""
import argparse,collections,json,math
from pathlib import Path
import numpy as np

class RowAllocator:
 def __init__(self,bounds,blocked=(),cell_size=(1.08,.27),column_pitch=2.16,row_pitch=.27,origin=(0.,0.),bucket_um=100.):
  self.bounds=tuple(map(float,bounds));self.cw,self.ch=map(float,cell_size);self.cp=float(column_pitch);self.rp=float(row_pitch);self.ox,self.oy=map(float,origin);self.bucket=float(bucket_um)
  if self.cp<self.cw or self.rp<self.ch:raise ValueError('site pitches smaller than cell footprint')
  x0,y0,x1,y1=self.bounds;self.ix0=math.ceil((x0-self.ox)/self.cp-1e-8);self.ix1=math.floor((x1-self.ox-self.cw)/self.cp+1e-8);self.iy0=math.ceil((y0-self.oy)/self.rp-1e-8);self.iy1=math.floor((y1-self.oy-self.ch)/self.rp+1e-8);self.nx=self.ix1-self.ix0+1;self.used=set();self.blocks=np.asarray(list(blocked),dtype=float).reshape((-1,4));self.index=collections.defaultdict(set)
  for i,(a,b,c,d) in enumerate(self.blocks):
   for tx in range(math.floor(a/self.bucket),math.floor(c/self.bucket)+1):
    for ty in range(math.floor(b/self.bucket),math.floor(d/self.bucket)+1):self.index[tx,ty].add(i)
 def _rectangles(self,x0,y0,x1,y1):
  ids=set()
  for tx in range(math.floor(x0/self.bucket),math.floor(x1/self.bucket)+1):
   for ty in range(math.floor(y0/self.bucket),math.floor(y1/self.bucket)+1):ids.update(self.index.get((tx,ty),()))
  return self.blocks[list(ids)] if ids else ()
 def project(self,target,clearance=4.32):
  """Nearest static macro-free centre; caller audits displacement to original target."""
  a,b,c,d=self.bounds;m=float(clearance);x=min(max(target[0],a+m),c-m);y=min(max(target[1],b+m),d-m)
  def valid(p):
   xx,yy=p
   return a+m-1e-8<=xx<=c-m+1e-8 and b+m-1e-8<=yy<=d-m+1e-8 and not any(u-m<xx<v+m and q-m<yy<r+m for u,q,v,r in self.blocks)
  if valid((x,y)):return x,y
  xs={a+m,c-m,*[z for u,q,v,r in self.blocks for z in (u-m,v+m)]};ys={b+m,d-m,*[z for u,q,v,r in self.blocks for z in (q-m,r+m)]};choices=[(xx,y) for xx in xs]+[(x,yy) for yy in ys];ok=[p for p in choices if valid(p)]
  if not ok:ok=[(xx,yy) for xx in xs for yy in ys if valid((xx,yy))]
  if not ok:raise ValueError('no macro-free projected centre')
  return min(ok,key=lambda p:abs(p[0]-target[0])+abs(p[1]-target[1]))
 def reserve_rectangle(self,rectangle):
  """Reserve every candidate footprint intersecting a fixed occupied rectangle."""
  a,b,c,d=map(float,rectangle)
  lo=max(self.ix0,math.floor((a-self.ox-self.cw)/self.cp)+1);hi=min(self.ix1,math.ceil((c-self.ox)/self.cp)-1)
  ly=max(self.iy0,math.floor((b-self.oy-self.ch)/self.rp)+1);hy=min(self.iy1,math.ceil((d-self.oy)/self.rp)-1)
  for iy in range(ly,hy+1):
   self.used.update((iy-self.iy0)*self.nx+ix-self.ix0 for ix in range(lo,hi+1))
 def allocate(self,target,count,max_radius_um=200.):
  count=int(count);x,y=map(float,target)
  if count<0:raise ValueError('negative count')
  if not count:return np.empty((0,2)),dict(count=0,max_distance_um=0.)
  radius=min(max_radius_um,max(self.cp,math.sqrt(count*self.cp*self.rp/2)+self.cp))
  while True:
   lo=max(self.ix0,math.ceil((x-radius-self.ox-self.cw/2)/self.cp));hi=min(self.ix1,math.floor((x+radius-self.ox-self.cw/2)/self.cp));ly=max(self.iy0,math.ceil((y-radius-self.oy-self.ch/2)/self.rp));hy=min(self.iy1,math.floor((y+radius-self.oy-self.ch/2)/self.rp))
   ix,iy=np.meshgrid(np.arange(lo,hi+1),np.arange(ly,hy+1));ix=ix.ravel();iy=iy.ravel();xs=self.ox+ix*self.cp+self.cw/2;ys=self.oy+iy*self.rp+self.ch/2;cost=np.abs(xs-x)+np.abs(ys-y);ids=(iy-self.iy0)*self.nx+(ix-self.ix0);ok=cost<=radius+1e-8
   for a,b,c,d in self._rectangles(x-radius-self.cw,y-radius-self.ch,x+radius+self.cw,y+radius+self.ch):ok &= ~((xs-self.cw/2<c-1e-8)&(xs+self.cw/2>a+1e-8)&(ys-self.ch/2<d-1e-8)&(ys+self.ch/2>b+1e-8))
   if self.used:ok &= np.fromiter((int(k) not in self.used for k in ids),bool,count=len(ids))
   valid=np.flatnonzero(ok)
   if len(valid)>=count:
    order=np.lexsort((ids[valid],cost[valid]));chosen=valid[order[:count]];self.used.update(map(int,ids[chosen]));sites=np.column_stack((xs[chosen],ys[chosen]));return sites,dict(count=count,max_distance_um=float(cost[chosen].max()),span_um=[float(np.ptp(sites[:,0])+self.cw),float(np.ptp(sites[:,1])+self.ch)])
   if radius>=max_radius_um-1e-8:raise ValueError(f'only{len(valid)} legal sites for{count} at{x,y} within{max_radius_um}um')
   radius=min(max_radius_um,radius*1.5+self.cp)

def main():
 p=argparse.ArgumentParser();p.add_argument('input',type=Path);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 if a.out.exists():raise FileExistsError(a.out)
 x=json.loads(a.input.read_text());allocator=RowAllocator(x['bounds'],x.get('blocked',()),**x.get('parameters',{}));out=[]
 for g in x['groups']:
  pts,stats=allocator.allocate(g['target'],g['count'],g.get('max_radius_um',200));out.append(dict(id=g['id'],sites_um=pts.tolist(),stats=stats))
 a.out.write_text(json.dumps(dict(scope=__doc__,groups=out),indent=1)+'\n')
if __name__=='__main__':main()
