"""Rectilinear START relay paths clear of macro/clock keepouts.

This helper only proposes sites. Callers must price the returned depth, bind the
changed plan and review its geometry before using it in a kit.
"""
from __future__ import annotations
import heapq
import math


def path(start, end, boxes, *, clearance_um=4.32, bounds=None):
    """Shortest rectilinear path outside closed expanded obstacle rectangles.

    Paths may follow an obstacle boundary: the expansion reserves clearance for
    the whole relay box, rather than merely keeping its centre outside a macro.
    An endpoint inside an expanded obstacle is an error, never silently moved.
    """
    start, end = tuple(start), tuple(end)
    obs = [(a-clearance_um,b-clearance_um,c+clearance_um,d+clearance_um)
           for a,b,c,d in boxes]
    def legal(p):
        x,y=p
        return (bounds is None or bounds[0]<=x<=bounds[2] and bounds[1]<=y<=bounds[3]) and not any(a<x<c and b<y<d for a,b,c,d in obs)
    if not legal(start) or not legal(end):
        raise ValueError('START endpoint inside keepout or outside outline')
    xs=sorted({start[0],end[0],*(x for r in obs for x in (r[0],r[2]))})
    ys=sorted({start[1],end[1],*(y for r in obs for y in (r[1],r[3]))})
    def clear(p,q):
        x,y=p; u,v=q
        if y==v:
            return not any(b<y<d and max(min(x,u),a)<min(max(x,u),c) for a,b,c,d in obs)
        return not any(a<x<c and max(min(y,v),b)<min(max(y,v),d) for a,b,c,d in obs)
    source=(xs.index(start[0]),ys.index(start[1])); target=(xs.index(end[0]),ys.index(end[1]))
    dist={source:0.0}; prev={}; todo=[(0.0,source)]
    while todo:
        cost,node=heapq.heappop(todo)
        if cost!=dist[node]: continue
        if node==target: break
        i,j=node; p=(xs[i],ys[j])
        for ni,nj in ((i-1,j),(i+1,j),(i,j-1),(i,j+1)):
            if not (0<=ni<len(xs) and 0<=nj<len(ys)): continue
            q=(xs[ni],ys[nj]); nxt=(ni,nj)
            if not legal(q) or not clear(p,q): continue
            nd=cost+abs(p[0]-q[0])+abs(p[1]-q[1])
            if nd<dist.get(nxt,math.inf):
                dist[nxt]=nd; prev[nxt]=node; heapq.heappush(todo,(nd,nxt))
    if target not in dist: raise ValueError('no legal START corridor')
    nodes=[target]
    while nodes[-1]!=source: nodes.append(prev[nodes[-1]])
    points=[(xs[i],ys[j]) for i,j in reversed(nodes)]
    compact=[]
    for p in points:
        while len(compact)>=2 and ((compact[-2][0]==compact[-1][0]==p[0]) or (compact[-2][1]==compact[-1][1]==p[1])): compact.pop()
        compact.append(p)
    return compact


def length(points):
    return sum(abs(a[0]-b[0])+abs(a[1]-b[1]) for a,b in zip(points,points[1:]))


def relay_sites(points, depth=None, *, max_hop_um=340.0, site_boxes=(), clearance_um=4.32):
    """Sites along the corridor, avoiding reserved cell boxes without adding wire detours.

    Macro rectangles belong in path(); storage/clock bands may carry wires but
    exclude relay cells, and therefore belong in site_boxes. A common explicit
    depth preserves aligned START branches. An infeasible depth fails closed.
    """
    total=length(points)
    needed=max(0,math.ceil(total/max_hop_um)-1)
    if depth is None: depth=needed
    if depth<needed: raise ValueError(f'START depth {depth} needs at least {needed} for corridor length {total}')
    forbidden=[];offset=0.0
    for a,b in zip(points,points[1:]):
        size=abs(a[0]-b[0])+abs(a[1]-b[1])
        for x0,y0,x1,y1 in site_boxes:
            x0-=clearance_um;y0-=clearance_um;x1+=clearance_um;y1+=clearance_um
            axis=0 if a[1]==b[1] else 1
            fixed=a[1-axis]
            lo,hi=(x0,x1) if axis==0 else (y0,y1)
            flo,fhi=(y0,y1) if axis==0 else (x0,x1)
            if not flo<fixed<fhi: continue
            seglo=max(min(a[axis],b[axis]),lo);seghi=min(max(a[axis],b[axis]),hi)
            if seglo>=seghi: continue
            u=offset+abs(seglo-a[axis]);v=offset+abs(seghi-a[axis])
            forbidden.append((min(u,v),max(u,v)))
        offset+=size
    def at(d):
        for a,b in zip(points,points[1:]):
            size=abs(a[0]-b[0])+abs(a[1]-b[1])
            if d<=size:
                frac=d/size if size else 0
                return [round(a[0]+frac*(b[0]-a[0]),3),round(a[1]+frac*(b[1]-a[1]),3)]
            d-=size
        return list(points[-1])
    sites=[];previous=0.0
    for k in range(1,depth+1):
        low=max(previous+0.001,total-(depth+1-k)*max_hop_um)
        high=min(total-0.001,previous+max_hop_um)
        ranges=[(low,high)]
        for lo,hi in forbidden:
            pieces=[]
            for a,b in ranges:
                if hi<=a or lo>=b: pieces.append((a,b));continue
                if a<lo: pieces.append((a,lo))
                if hi<b: pieces.append((hi,b))
            ranges=pieces
        if not ranges: raise ValueError('START depth has no legal relay site before maximum hop')
        ideal=total*k/(depth+1)
        d=min((min(max(ideal,a),b) for a,b in ranges),key=lambda x:abs(x-ideal))
        sites.append(at(d));previous=d
    return sites
