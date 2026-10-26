"""Constructive fallback when greedy projection oscillates inside a core/slit union.
Existing legal projections stay unchanged. For rejected points only, a cached
2um rectilinear free-space grid supplies an actual legal site; the FT allocator
and exact final Manhattan hop gate still decide the resulting station chain.
No timing, reach or keepoff budget is widened.
"""
import numpy as np
_CACHE={}
def free_grid(boxes,bounds,inside):
    key=tuple(tuple(b) for b in boxes),tuple(bounds)
    if key in _CACHE:return _CACHE[key]
    x0,y0,x1,y1=bounds;step=2.0
    xs=np.arange(x0,x1+.001,step);ys=np.arange(y0,y1+.001,step)
    xx,yy=np.meshgrid(xs,ys);pts=np.column_stack([xx.ravel(),yy.ravel()]);blocked=inside(pts,boxes).reshape(len(ys),len(xs))
    ny,nx=blocked.shape;INF=10**8;dist=np.where(blocked,INF,0).astype(np.int32);src=np.arange(nx*ny,dtype=np.int32).reshape(ny,nx)
    for y in range(ny):
        for x in range(nx):
            if dist[y,x]==0:continue
            if y and dist[y-1,x]+1<dist[y,x]:dist[y,x]=dist[y-1,x]+1;src[y,x]=src[y-1,x]
            if x and dist[y,x-1]+1<dist[y,x]:dist[y,x]=dist[y,x-1]+1;src[y,x]=src[y,x-1]
    for y in range(ny-1,-1,-1):
        for x in range(nx-1,-1,-1):
            if dist[y,x]==0:continue
            if y+1<ny and dist[y+1,x]+1<dist[y,x]:dist[y,x]=dist[y+1,x]+1;src[y,x]=src[y+1,x]
            if x+1<nx and dist[y,x+1]+1<dist[y,x]:dist[y,x]=dist[y,x+1]+1;src[y,x]=src[y,x+1]
    value=(pts,src,dist,bounds,step);_CACHE[key]=value;return value

def project(pts,boxes,bounds,base,inside):
    q,d=base(pts,boxes,bounds);bad=~np.isfinite(d)
    if not bad.any():return q,d
    grid,src,gd,(x0,y0,x1,y1),step=free_grid(boxes,bounds,inside)
    ix=np.clip(np.rint((pts[bad,0]-x0)/step).astype(int),0,src.shape[1]-1)
    iy=np.clip(np.rint((pts[bad,1]-y0)/step).astype(int),0,src.shape[0]-1)
    picks=grid[src[iy,ix]];valid=gd[iy,ix]<10**8
    q[bad]=picks;d[bad]=np.where(valid,np.abs(picks-pts[bad]).sum(axis=1),np.inf)
    if inside(q[np.isfinite(d)],boxes).any():raise ValueError("union projection returned a blocked point")
    return q,d
