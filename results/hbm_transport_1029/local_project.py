"""Private vector projection using only blockers near the current point cloud.

Large HBM frames contain thousands of protected banks. Testing every bank for
every candidate point dominated construction time. A vector bounding-box filter
selects relevant rectangles each pass. Final points are checked against every
blocker intersecting their actual cloud; blocked points return infinite cost.
This only proposes geometry; unchanged full legal-row/hop gates remain final.
"""
import numpy as np
_CACHE=[None,None]

def project(points,boxes,bounds):
    if _CACHE[0] is not boxes:
        _CACHE[:]=[boxes,np.asarray(boxes,float).reshape((-1,4))]
    B=_CACHE[1];x0,y0,x1,y1=bounds
    q=np.column_stack((np.clip(points[:,0],x0,x1),np.clip(points[:,1],y0,y1)))
    def relevant():
        if not len(B):return B
        lo=q.min(axis=0);hi=q.max(axis=0)
        return B[(B[:,0]<hi[0])&(B[:,2]>lo[0])&(B[:,1]<hi[1])&(B[:,3]>lo[1])]
    for _ in range(3):
        moved=False
        for a,b,c,d in relevant():
            hit=(q[:,0]>a)&(q[:,0]<c)&(q[:,1]>b)&(q[:,1]<d)
            if not hit.any():continue
            moved=True;p=q[hit]
            choices=np.stack([np.column_stack((np.full(len(p),a-.01),p[:,1])),
                              np.column_stack((np.full(len(p),c+.01),p[:,1])),
                              np.column_stack((p[:,0],np.full(len(p),b-.01))),
                              np.column_stack((p[:,0],np.full(len(p),d+.01)))])
            cost=np.abs(choices-p[None]).sum(axis=2)
            for i,lim in enumerate(((x0,None),(None,x1),(y0,None),(None,y1))):
                v=choices[i][:,i//2]
                if lim[0] is not None:cost[i][v<lim[0]]=np.inf
                if lim[1] is not None:cost[i][v>lim[1]]=np.inf
            q[hit]=choices[np.argmin(cost,axis=0),np.arange(len(p))]
        if not moved:break
    bad=np.zeros(len(q),bool)
    for a,b,c,d in relevant():bad|=(q[:,0]>a)&(q[:,0]<c)&(q[:,1]>b)&(q[:,1]<d)
    return q,np.where(bad,np.inf,np.abs(q-points).sum(axis=1))

def install(module):module.project=project
