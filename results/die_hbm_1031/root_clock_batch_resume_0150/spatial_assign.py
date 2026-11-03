import numpy as np

def nearest(xy, points):
    xy=np.asarray(xy,dtype=float);points=np.asarray(points,dtype=float)
    best=np.full(len(points),np.inf);ans=np.full(len(points),len(xy),dtype=np.int64)
    def build(ids):
        p=xy[ids];lo=p.min(0);hi=p.max(0)
        if len(ids)<=8:return(lo,hi,np.sort(ids),None)
        ax=int(np.argmax(hi-lo));ids=ids[np.argsort(p[:,ax],kind='stable')];m=len(ids)//2
        cut=(xy[ids[m-1],ax]+xy[ids[m],ax])/2
        return(lo,hi,None,(ax,cut,build(ids[:m]),build(ids[m:])))
    def visit(node, ids):
        if not len(ids):return
        lo,hi,leaf,children=node;p=points[ids,:2]
        bound=np.maximum(lo-p,0).sum(1)+np.maximum(p-hi,0).sum(1)
        ids=ids[bound<=best[ids]+1e-8]
        if not len(ids):return
        if leaf is not None:
            p=points[ids,:2]
            for j in leaf:
                d=np.abs(p-xy[j]).sum(1);old=best[ids]
                take=(d<old)|((d==old)&(j<ans[ids]));ii=ids[take]
                best[ii]=d[take];ans[ii]=j
            return
        ax,cut,left,right=children;mask=points[ids,ax]<=cut;a=ids[mask];b=ids[~mask]
        visit(left,a);visit(right,a);visit(right,b);visit(left,b)
    visit(build(np.arange(len(xy))),np.arange(len(points)))
    # Break recursive closure cycles before returning large NumPy buffers.
    build=None;visit=None
    return ans

def assign(taps,sinks,cap,max_extra_um,max_distance_um=None):
    xy=np.asarray([(t[1],t[2]) for t in taps]);ss=np.asarray(sinks);k=len(xy)
    a=nearest(xy,ss[:,:2]);load=np.bincount(a,weights=ss[:,2],minlength=k);stuck=set()
    for _ in range(8*k):
        over=next((j for j in range(k)if j not in stuck and load[j]>cap),None)
        if over is None:break
        cand=[]
        for i in np.where(a==over)[0]:
            d=np.abs(ss[i,:2]-xy).sum(1);js=np.where((np.arange(k)!=over)&(load<cap)&((d<=max_distance_um)if max_distance_um is not None else True))[0]
            if not len(js):continue
            j=js[np.argmin(d[js])];extra=d[j]-d[over]
            if extra<=max_extra_um:cand.append((extra,int(i),int(j)))
        if not cand:stuck.add(over);continue
        cand.sort();tgt=cand[0][2]
        for _,i,j in cand:
            if load[over]<=cap or load[tgt]>=cap:break
            if j!=tgt:continue
            a[i]=tgt;load[over]-=ss[i,2];load[tgt]+=ss[i,2]
    far=np.zeros(k);dist=np.abs(ss[:,:2]-xy[a]).sum(1);np.maximum.at(far,a,dist)
    return load,far,a

if __name__=='__main__':
    import random
    random.seed(1025)
    for case in range(100):
        xy=np.array([(random.randrange(-20,20),random.randrange(-20,20))for _ in range(32)],float)
        pts=np.array([(random.randrange(-30,30),random.randrange(-30,30))for _ in range(100)],float)
        got=nearest(xy,pts);want=np.array([min(range(len(xy)),key=lambda j:(abs(p[0]-xy[j,0])+abs(p[1]-xy[j,1]),j))for p in pts])
        assert np.array_equal(got,want),(case,np.where(got!=want))
    print('EXACT_NEAREST_REFERENCE_100_PASS')
