"""Exact footprint bays for a forwarded spine; strict405um routed reach.

Large hard macros remain obstacles. Reset repeater cells are refined from the
coarse grid into real site-sized bays. All already placed region/std cells are
included, and every emitted spine footprint is reserved before the next route.
"""
import math
from collections import defaultdict
import regtree as rt
from qwen_corridor_audit import bay, overlap, XP, YP


class ExactBayGrid(rt.dct.Grid):
    def __init__(self,width,height,rows):
        self.rows=rows
        super().__init__(width,height,[r for _,r in rows])
        affected=set()
        for name,(x0,y0,x1,y1) in rows:
            if name.startswith('rstt_'):
                affected.update((i,j) for i in range(int(x0//rt.GRID),math.ceil(x1/rt.GRID))
                                for j in range(int(y0//rt.GRID),math.ceil(y1/rt.GRID)))
        self.boxes=defaultdict(list)
        for _,r in rows:
            for i in range(max(0,int(r[0]//rt.GRID)),min(self.nx,math.ceil(r[2]/rt.GRID))):
                for j in range(max(0,int(r[1]//rt.GRID)),min(self.ny,math.ceil(r[3]/rt.GRID))):
                    if (i,j) in affected:self.boxes[i,j].append(r)
        self.points={}
        for c in affected:
            p=bay(c,self.boxes[c])
            if p is not None:self.points[c]=p;self.blk[c[1]*self.nx+c[0]]=0
        self.refined_cells=len(self.points)

    def point(self,c):
        if not self.free(c):return None
        if c not in self.points:self.points[c]=bay(c,self.boxes[c])
        return self.points[c]

    def reserve(self,c):
        p=self.point(c)
        if p is None:raise ValueError('no whole clock footprint bay: '+str(c))
        x,y=p;self.boxes[c].append((x,y,x+XP,y+YP))
        nxt=bay(c,self.boxes[c]);self.points[c]=nxt
        self.blk[c[1]*self.nx+c[0]]=int(nxt is None)
        return tuple(p)

    def route_reserved(self,a,b,max_run=380):
        # The two endpoint footprints are already reserved, but are legal
        # stage endpoints. Only these two cells may reset the blocked run.
        saved={c:self.blk[c[1]*self.nx+c[0]] for c in (a,b)}
        try:
            for c in saved:self.blk[c[1]*self.nx+c[0]]=0
            return self._route(a,b,max_run)
        finally:
            for c,v in saved.items():self.blk[c[1]*self.nx+c[0]]=v

    def route(self,a,b,max_run=None):
        # Local trees reserve another40um for boundary cells and actual pin
        # offsets. No legacy1200um macro-escape fallback is available.
        run=min(340,max_run or 340);path=self.route_reserved(a,b,run)
        if not any(self.free(c) for c in path):
            # Two already reserved endpoints can occupy the same full cell.
            # A merge still needs a distinct legal physical footprint.
            mid=self.nearest_free(*self.xy(a))
            path=self.route_reserved(a,mid,run)+self.route_reserved(mid,b,run)[1:]
        return path


class ExactRegionalBuilder(rt.Builder):
    """Keep local DME/native targets, reserve full footprints during modelling."""
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs);self.buf_cells={}

    def newbuf(self,tag,c,cell=rt.BUF):
        if not self.g.free(c):c=self.g.nearest_free(*self.g.xy(c))
        p=self.g.reserve(c);self.cnt[tag]+=1;n=f'{self.prefix}_{tag}{self.cnt[tag]}'
        self.bufs.append([n,cell,*p]);self.buf_cells[n]=c
        return n

    def leaf(self,pts):
        result=super().leaf(pts);name=result['buf'];result['cell']=self.buf_cells[name]
        x,y=next((b[2],b[3]) for b in reversed(self.bufs) if b[0]==name)
        bound=max(abs(s[2]-x)+abs(s[3]-y)+XP+YP for s in pts)
        if bound>405+1e-7:raise ValueError(f'exact regional leaf needs corridor/partition: {name} {bound:.3f}um >405')
        return result

    def merge(self,a,b):
        result=super().merge(a,b);result['cell']=self.buf_cells[result['buf']]
        return result


def routed_bound(path,start,end,grid):
    return (len(path)-1)*rt.GRID+sum(abs(start[i]-grid.xy(path[0])[i])+
                                      abs(end[i]-grid.xy(path[-1])[i]) for i in (0,1))


def check_reach(path,start,end,grid):
    length=routed_bound(path,start,end,grid)
    if length>405+1e-7:raise ValueError(f'placed forwarded clock routed reach {length:.3f}um >405')
    return length


class ExactForwardedBuilder:
    def __init__(self,grid,prefix):
        self.g,self.prefix=grid,prefix
        self.bufs=[];self.nets=[];self.parent={};self.positions={};self.edges=[]

    def node(self,xy):
        c=self.g.nearest_free(*xy);p=self.g.reserve(c)
        n=f'{self.prefix}_E{len(self.bufs)+1}'
        self.bufs.append([n,rt.BUF,*p]);self.positions[n]=p
        return ('buf',n),p

    def connect(self,driver,source,target,dest):
        path=self.g.route_reserved(self.g.cell(*source),self.g.cell(*dest))
        cursor=0;at=source;drv=driver
        while cursor<len(path)-1:
            eligible=[]
            for k in range(cursor+1,min(len(path),cursor+42)):
                p=dest if k==len(path)-1 else self.g.point(path[k])
                if p is not None and routed_bound(path[cursor:k+1],at,p,self.g)<=405+1e-7:
                    eligible.append((k,p))
            if not eligible:raise ValueError('no <=405um exact-bay continuation from '+str(path[cursor]))
            k,p=eligible[-1]
            if k==len(path)-1:load=target
            else:
                p=self.g.reserve(path[k]);n=f'{self.prefix}_E{len(self.bufs)+1}'
                self.bufs.append([n,rt.BUF,*p]);self.positions[n]=p;load=('buf',n)
            length=check_reach(path[cursor:k+1],at,p,self.g)
            self.nets.append([f'n_{self.prefix}_{len(self.nets)}',drv,[load]])
            self.parent[load[1]]=drv[1]
            self.edges.append(dict(driver=drv,load=load,source_xy=at,target_xy=p,
                                   route_cells=path[cursor:k+1],routed_bound_um=length))
            drv,at,cursor=load,p,k
        if len(path)==1:
            length=check_reach(path,source,dest,self.g)
            self.nets.append([f'n_{self.prefix}_{len(self.nets)}',driver,[target]])
            self.parent[target[1]]=driver[1]
            self.edges.append(dict(driver=driver,load=target,source_xy=source,target_xy=dest,
                                   route_cells=path,routed_bound_um=length))

    def subtree(self,leaves):
        centers=[(sum(s[2] for s in l)/len(l),sum(s[3] for s in l)/len(l)) for l in leaves]
        if len(leaves)==1:
            driver,pos=self.node(centers[0])
            for pin,_,x,y,_ in leaves[0]:self.connect(driver,pos,('pin',pin),(x,y))
            return driver,pos
        axis=int(max(p[1] for p in centers)-min(p[1] for p in centers)>
                 max(p[0] for p in centers)-min(p[0] for p in centers))
        order=sorted(range(len(leaves)),key=lambda i:(centers[i][axis],centers[i][1-axis]))
        half=len(order)//2
        children=[self.subtree([leaves[i] for i in ids]) for ids in (order[:half],order[half:])]
        root,pos=self.node(tuple(sorted(p[i] for p in centers)[len(centers)//2] for i in (0,1)))
        for child,cp in children:self.connect(root,pos,child,cp)
        return root,pos

    def build(self,root_pin,root_xy,leaves):
        root,pos=self.subtree(leaves);self.connect(('pin',root_pin),root_xy,root,pos)
        merged={}
        for name,drv,loads in self.nets:
            if drv in merged:merged[drv][2].extend(loads)
            else:merged[drv]=[name,drv,list(loads)]
        self.nets=list(merged.values())
        if any(len(loads)>2 for _,_,loads in self.nets):raise ValueError('exact forwarded fanout exceeds two')
        return dict(top=root[1],topology='forwarded_exact_bays',leaves=len(leaves),buffers=len(self.bufs),
                    pads=0,region_insertion_compensated=False,max_route_segment_um=405,
                    max_placed_routed_bound_um=max(e['routed_bound_um'] for e in self.edges),
                    exact_bay_refined_cells=self.g.refined_cells)
