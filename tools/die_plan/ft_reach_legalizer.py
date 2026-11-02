"""Opt-in single-cell FT row legalizer with actual adjacent-hop constraints."""
import math
import numpy as np
from tools.die_trial.legal_sites import RowAllocator

class ReachAllocator(RowAllocator):
 def allocate_reachable(self,target,previous,following,reach=405.,max_radius_um=80.):
  if reach<=0 or max_radius_um<0:raise ValueError('invalid reach/radius')
  x,y=map(float,target);radius=min(max_radius_um,self.cp)
  while True:
   lo=max(self.ix0,math.ceil((x-radius-self.ox-self.cw/2)/self.cp));hi=min(self.ix1,math.floor((x+radius-self.ox-self.cw/2)/self.cp))
   ly=max(self.iy0,math.ceil((y-radius-self.oy-self.ch/2)/self.rp));hy=min(self.iy1,math.floor((y+radius-self.oy-self.ch/2)/self.rp))
   ix,iy=np.meshgrid(np.arange(lo,hi+1),np.arange(ly,hy+1));ix=ix.ravel();iy=iy.ravel()
   xs=self.ox+ix*self.cp+self.cw/2;ys=self.oy+iy*self.rp+self.ch/2;cost=abs(xs-x)+abs(ys-y);ids=(iy-self.iy0)*self.nx+ix-self.ix0
   ok=cost<=radius+1e-8
   for px,py in (previous,following):ok&=(abs(xs-px)+abs(ys-py)<=reach+1e-8)
   for a,b,c,d in self._rectangles(x-radius-self.cw,y-radius-self.ch,x+radius+self.cw,y+radius+self.ch):
    ok&=~((xs-self.cw/2<c-1e-8)&(xs+self.cw/2>a+1e-8)&(ys-self.ch/2<d-1e-8)&(ys+self.ch/2>b+1e-8))
   if self.used:ok&=np.fromiter((int(k)not in self.used for k in ids),bool,count=len(ids))
   valid=np.flatnonzero(ok)
   if len(valid):
    order=np.lexsort((ids[valid],cost[valid]));chosen=valid[order[0]];self.used.add(int(ids[chosen]));point=(float(xs[chosen]),float(ys[chosen]))
    return point,dict(distance_um=float(cost[chosen]),previous_hop_um=sum(abs(a-b)for a,b in zip(point,previous)),following_target_hop_um=sum(abs(a-b)for a,b in zip(point,following)))
   if radius>=max_radius_um-1e-8:raise ValueError(f'no legal reachable cell at{target} within{max_radius_um}um; prev={previous} next={following} reach={reach}')
   radius=min(max_radius_um,radius*1.5+self.cp)

def install_reach_slot(module, destination):
 """Explicit opt-in adapter; native FT search stays intact, only row picking changes."""
 import inspect
 from pathlib import Path
 source=inspect.getsource(module._slot);lines=source.splitlines();hits=[]
 for i,line in enumerate(lines):
  if line.strip()=='q, _ = al.allocate(np.array(p), 1, max_radius_um=20.)':hits.append(i)
 if len(hits)!=1:raise ValueError('native FT allocator call changed; review adapter')
 i=hits[0];indent=lines[i][:-len(lines[i].lstrip())]
 following=lines[i+1]
 if not following.lstrip().startswith('c = q[0]; sites[j][b] = '):raise ValueError('native FT row assignment changed')
 assignment=following.lstrip()[len('c = q[0]; '):]
 replacement=[
  'previous=ia if j==0 else (sites[j-1][b][0]+CELL[0]/2,sites[j-1][b][1]+CELL[1]/2)',
  'following=ps[j+1] if j+1<len(ps) else ib',
  'try: c, _ = al.allocate_reachable(np.array(p),previous,following,reach=smax,max_radius_um=80.)',
  "except ValueError as e: raise ValueError(f'{tn}/{name} bit{b} stage{j+1}: {e}') from e",
  assignment]
 lines[i:i+2]=[indent+x for x in replacement];source='\n'.join(lines)+'\n';code=compile(source,str(destination),'exec')
 Path(destination).write_text(source);exec(code,module.__dict__)
 return source
