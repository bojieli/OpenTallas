"""Conservative explicit FT station banks around hard cores (KV split forms).

The caller supplies the actual bit-face flop sites, not a bus centroid.  Each bit
follows a rectilinear free-space path.  Intermediate flops occupy distinct legal
ASAP7 grid cells; equal stage counts preserve bundle coherence.  Added stages are
part of the returned station count and must be priced by the parent lane table.
"""
from functools import lru_cache
import heapq
import math

CELL_UM = (1.404, 0.27)  # the existing KV explicit-FT cell envelope (1009 POR slots)
PITCH_UM = (2.16, 1.08)  # 40 placement sites by four rows, conservative bank spacing
EPS = 1e-6


class StationPathError(ValueError):
    pass


def _box(h):
    x, y = h["origin_um"]
    dx, dy = h.get("track_offset_um", [0, 0])
    w, hh = h["outline_um"]
    if h.get("orient", "R0") in ("R90", "R270", "MXR90", "MYR90"):
        w, hh = hh, w
    return x+dx, y+dy, x+dx+w, y+dy+hh


class _Router:
    def __init__(self, outline, cores, halo):
        self.w, self.h = map(float, outline)
        self.boxes = [(x0-halo, y0-halo, x1+halo, y1+halo)
                      for x0, y0, x1, y1 in map(_box, cores)]

    def free(self, p):
        x, y = p
        return (-EPS <= x <= self.w+EPS and -EPS <= y <= self.h+EPS and
                not any(a+EPS < x < c-EPS and b+EPS < y < d-EPS for a,b,c,d in self.boxes))

    def edge(self, p, q):
        x,y=p; xx,yy=q
        if abs(x-xx) < EPS:
            lo,hi=sorted((y,yy))
            return not any(a+EPS<x<c-EPS and min(hi,d)-max(lo,b)>EPS for a,b,c,d in self.boxes)
        if abs(y-yy) < EPS:
            lo,hi=sorted((x,xx))
            return not any(b+EPS<y<d-EPS and min(hi,c)-max(lo,a)>EPS for a,b,c,d in self.boxes)
        return False

    @lru_cache(maxsize=16384)
    def path(self, a, z):
        if not self.free(a) or not self.free(z):
            raise StationPathError(f"endpoint in macro halo: {a} -> {z}")
        if a == z:
            return (a,)
        xs=sorted({a[0],z[0],0.0,self.w}|{v for b in self.boxes for v in (b[0],b[2]) if 0<=v<=self.w})
        ys=sorted({a[1],z[1],0.0,self.h}|{v for b in self.boxes for v in (b[1],b[3]) if 0<=v<=self.h})
        ix={v:i for i,v in enumerate(xs)}; iy={v:i for i,v in enumerate(ys)}
        start=(ix[a[0]],iy[a[1]]); target=(ix[z[0]],iy[z[1]])
        def point(k):return (xs[k[0]],ys[k[1]])
        queue=[(0.0,start)]; dist={start:0.0}; parent={}
        while queue:
            cost,u=heapq.heappop(queue)
            if cost>dist[u]+EPS:continue
            if u==target:
                out=[]
                while True:
                    out.append(point(u))
                    if u==start:break
                    u=parent[u]
                return tuple(reversed(out))
            x,y=u
            for v in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
                if not (0<=v[0]<len(xs) and 0<=v[1]<len(ys)):continue
                p,q=point(u),point(v)
                if not self.free(q) or not self.edge(p,q):continue
                nxt=cost+abs(p[0]-q[0])+abs(p[1]-q[1])
                if nxt+EPS<dist.get(v,float("inf")):
                    dist[v]=nxt;parent[v]=u;heapq.heappush(queue,(nxt,v))
        raise StationPathError(f"no macro-clear path {a} -> {z}")

    def length(self,a,z):
        p=self.path(tuple(a),tuple(z))
        return sum(abs(x[0]-y[0])+abs(x[1]-y[1]) for x,y in zip(p,p[1:]))


def _at(path, fraction):
    lengths=[abs(a[0]-b[0])+abs(a[1]-b[1]) for a,b in zip(path,path[1:])]
    rem=sum(lengths)*fraction
    for a,b,n in zip(path,path[1:],lengths):
        if rem<=n+EPS:
            t=rem/n if n else 0.0
            return (a[0]+(b[0]-a[0])*t,a[1]+(b[1]-a[1])*t)
        rem-=n
    return path[-1]


def plan_slot(outline_um, hard_cores, start_sites, end_sites, *, reach=405.0,
              halo=4.32, occupied=None, occupied_rects=(), bit_site_cell_um=CELL_UM,
              pitch_um=PITCH_UM, search_um=140.0):
    """Return complete slot station geometry; raises if any bit cannot be placed.

    ``occupied`` is an optional mutable set of (grid_x,grid_y) shared across new
    slots of one type.  It changes only on success.  Coordinates are lower-left
    cell origins, as required by bit_sites_um.  Existing face-flop sites remain
    stage zero; returned explicit arrays cover stages one and later.
    occupied_rects contains arbitrary existing cell envelopes (x,y,w,h), such as
    inherited explicit FT banks and face flops; these block cells, not wires.
    """
    a=[tuple(map(float,p[:2])) for p in start_sites]
    z=[tuple(map(float,p[:2])) for p in end_sites]
    if not a or len(a)!=len(z):raise StationPathError("empty or unequal bit endpoints")
    if reach<=0:raise StationPathError("reach must be positive")
    cw,ch=map(float,bit_site_cell_um); px,py=map(float,pitch_um)
    if px<cw-EPS or py<ch-EPS:raise StationPathError("packing grid smaller than cell envelope")
    router=_Router(outline_um,hard_cores,float(halo))
    paths=[router.path(p,q) for p,q in zip(a,z)]
    lengths=[sum(abs(p[0]-q[0])+abs(p[1]-q[1]) for p,q in zip(path,path[1:])) for path in paths]
    # Reserve 160 um per hop for wide-bank legalization; cycles are cheap.
    stages=max(1,math.ceil(max(lengths)/max(1.0,reach-160.0)))
    used=set(occupied or ())
    w,h=map(float,outline_um)
    blocked_grid=set()
    for bx,by,bw,bh in occupied_rects:
        # Index arbitrary face/old-FT envelopes once: full types have tens of
        # thousands of face flops, so a linear scan per candidate is prohibitive.
        for ix in range(math.floor((bx-cw)/px)-1, math.ceil((bx+bw)/px)+2):
            for iy in range(math.floor((by-ch)/py)-1, math.ceil((by+bh)/py)+2):
                x,y=ix*px,iy*py
                if min(x+cw,bx+bw)-max(x,bx)>EPS and min(y+ch,by+bh)-max(y,by)>EPS:
                    blocked_grid.add((ix,iy))
    def legal(ix,iy):
        x,y=ix*px,iy*py
        if (ix,iy) in blocked_grid or x<-EPS or y<-EPS or x+cw>w+EPS or y+ch>h+EPS:return False
        return not any(min(x+cw,c)-max(x,bx)>EPS and min(y+ch,d)-max(y,by)>EPS
                       for bx,by,c,d in router.boxes)
    def candidates(target):
        gx=int(round(target[0]/px));gy=int(round(target[1]/py))
        rx=math.ceil(search_um/px);ry=math.ceil(search_um/py)
        # A metric heap avoids generating every point in a 140-um rectangle.
        heap=[(0.0,0,0)];seen={(0,0)}
        while heap:
            _,dx,dy=heapq.heappop(heap)
            ix,iy=gx+dx,gy+dy
            if abs(dx)<=rx and abs(dy)<=ry:
                yield ix,iy
                for nx,ny in ((dx-1,dy),(dx+1,dy),(dx,dy-1),(dx,dy+1)):
                    if abs(nx)>rx or abs(ny)>ry or (nx,ny) in seen:continue
                    seen.add((nx,ny));heapq.heappush(heap,(abs(nx)*px+abs(ny)*py,nx,ny))
    previous=list(a); explicit=[]; max_hop=0.0
    for stage in range(1,stages):
        sites=[]
        for bit,path in enumerate(paths):
            target=_at(path,stage/stages)
            found=None
            for ix,iy in candidates(target):
                if (ix,iy) in used or not legal(ix,iy):continue
                q=(round(ix*px,6),round(iy*py,6))
                # Both the preceding hop and remaining shortest path must fit.
                d=router.length(previous[bit],q)
                if d>reach-EPS:continue
                if router.length(q,z[bit])>(stages-stage)*reach-EPS:continue
                found=q;used.add((ix,iy));max_hop=max(max_hop,d);break
            if found is None:
                raise StationPathError(f"no legal bank site stage {stage}/{stages}, bit {bit}, target {target}")
            sites.append(list(found))
        explicit.append(sites);previous=[tuple(p) for p in sites]
    for p,q in zip(previous,z):
        d=router.length(p,q)
        if d>reach+EPS:raise StationPathError(f"last hop {d:.3f} exceeds {reach}")
        max_hop=max(max_hop,d)
    if occupied is not None:occupied.update(used)
    regs=[[sum(p[k] for p in a)/len(a) for k in (0,1)]]
    regs += [[sum(p[k] for p in row)/len(row) for k in (0,1)] for row in explicit]
    return dict(stations=stages,regs_um=regs,bit_sites_um=explicit,
                bit_site_cell_um=[cw,ch],station_path_report=dict(width=len(a),
                max_actual_bit_hop_um=round(max_hop,6),max_path_um=round(max(lengths),6),
                halo_um=halo,pitch_um=[px,py],cell_um=[cw,ch]))
