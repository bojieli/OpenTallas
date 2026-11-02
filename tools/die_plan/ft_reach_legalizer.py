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

def _weighted_distance(mask, pitches):
 d=np.where(mask,0.,1e9)
 for axis,pitch in enumerate(pitches):
  shape=[1]*d.ndim;shape[axis]=d.shape[axis];q=np.arange(d.shape[axis]).reshape(shape)*pitch
  left=np.minimum.accumulate(d-q,axis=axis)+q
  right=np.flip(np.minimum.accumulate(np.flip(d+q,axis=axis),axis=axis),axis=axis)-q
  d=np.minimum(left,right)
 return d

def _allocate_chain(self,start,goal,targets,reach=404.5):
 """Atomic fixed-count path on actual unoccupied row cells; no reservations cached."""
 if not targets or reach<=0:raise ValueError('invalid fixed-count chain')
 xs=self.ox+np.arange(self.ix0,self.ix1+1)*self.cp+self.cw/2
 ys=self.oy+np.arange(self.iy0,self.iy1+1)*self.rp+self.ch/2
 X,Y=xs[:,None],ys[None,:];free=np.ones((len(xs),len(ys)),dtype=bool)
 for a,b,c,d in self.blocks:
  free&=~((X-self.cw/2<c-1e-8)&(X+self.cw/2>a+1e-8)&(Y-self.ch/2<d-1e-8)&(Y+self.ch/2>b+1e-8))
 if self.used:
  occupied=np.fromiter(self.used,dtype=np.int64);free[occupied%self.nx,occupied//self.nx]=False
 backwards=[None]*len(targets);backwards[-1]=free&(abs(X-goal[0])+abs(Y-goal[1])<=reach+1e-8)
 for j in range(len(targets)-2,-1,-1):backwards[j]=free&(_weighted_distance(backwards[j+1],(self.cp,self.rp))<=reach+1e-8)
 chosen=[];ids=[];previous=start
 for j,target in enumerate(targets):
  lo=int(np.searchsorted(xs,previous[0]-reach));hi=int(np.searchsorted(xs,previous[0]+reach,side='right'))
  bot=int(np.searchsorted(ys,previous[1]-reach));top=int(np.searchsorted(ys,previous[1]+reach,side='right'))
  x,y=xs[lo:hi,None],ys[None,bot:top]
  ok=free[lo:hi,bot:top]&backwards[j][lo:hi,bot:top]&(abs(x-previous[0])+abs(y-previous[1])<=reach+1e-8)
  if not ok.any():raise ValueError(f'no fixed{len(targets)+1} occupied-row path atstage{j+1} underretainedreservations')
  cost=np.where(ok,abs(x-target[0])+abs(y-target[1]),np.inf)
  # Deterministic row-major ties, matching the base row allocator.
  row,col=np.unravel_index(np.argmin(cost.T),cost.T.shape);ix,iy=lo+col,bot+row
  previous=(float(xs[ix]),float(ys[iy]));chosen.append(previous);ids.append(int(iy*self.nx+ix));free[ix,iy]=False
 chain=[start,*chosen,goal];worst=max(sum(abs(x-y)for x,y in zip(a,b))for a,b in zip(chain,chain[1:]))
 if worst>reach+1e-6 or len(set(ids))!=len(ids):raise AssertionError('invalid actual-row path')
 self.used.update(ids)
 return chosen,dict(allocated=len(ids),max_hop_um=worst,grid_shape=free.shape,reservations_retained=len(self.used)-len(ids))

ReachAllocator.allocate_chain=_allocate_chain
