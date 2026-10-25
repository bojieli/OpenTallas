"""Orthogonal clock wires outside explicitly reserved PHY power domains.

Geometry only: returns physical wire-length deltas, never a timing/skew verdict.
Each input edge retains its level; added bends change wire layers M8 H / M9 V.
Shared endpoints move together. Separate edges remain separate nets/tracks even
where their geometric corridor is shared; reserve routing capacity accordingly.
"""
import heapq
import math


def inside(p, r):
    return r[0] < p[0] < r[2] and r[1] < p[1] < r[3]


def intersects(a, b, r):
    if abs(a[1] - b[1]) < 1e-7:
        return r[1] < a[1] < r[3] and min(a[0], b[0]) < r[2] and max(a[0], b[0]) > r[0]
    if abs(a[0] - b[0]) < 1e-7:
        return r[0] < a[0] < r[2] and min(a[1], b[1]) < r[3] and max(a[1], b[1]) > r[1]
    raise ValueError('clock corridor edge is not orthogonal')


def legalize(p, boxes, die_wh, taken=(), separation=8.64):
    if not any(inside(p, r) for r in boxes):
        return p
    W, H = die_wh
    xs = {p[0]} | {v for r in boxes for v in (r[0], r[2]) if 0 <= v <= W}
    ys = {p[1]} | {v for r in boxes for v in (r[1], r[3]) if 0 <= v <= H}
    candidates = [(x, y) for x in xs for y in ys if not any(inside((x, y), r) for r in boxes)]
    if not candidates:
        raise ValueError(f'PHY domains leave no legal clock endpoint near {p}')
    candidates.sort(key=lambda q: (abs(q[0]-p[0])+abs(q[1]-p[1]),q))
    def available(q):
        return 0<=q[0]<=W and 0<=q[1]<=H and not any(inside(q,r) for r in boxes) and all(
            abs(q[0]-t[0])+abs(q[1]-t[1]) >= separation-1e-7 for t in taken)
    for ring in range(401):
        d=ring*separation
        options={q for c in candidates for q in ((c[0]+d,c[1]),(c[0]-d,c[1]),
                                                 (c[0],c[1]+d),(c[0],c[1]-d)) if available(q)}
        if options:
            return min(options,key=lambda q:(abs(q[0]-p[0])+abs(q[1]-p[1]),q))
    raise ValueError(f'no separated legal clock endpoint near {p}')


def route(a, b, boxes, die_wh):
    """Shortest rectilinear visibility-grid route; obstacle boundaries are legal."""
    if a == b:
        return [a]
    if (a[0] == b[0] or a[1] == b[1]) and not any(intersects(a, b, r) for r in boxes):
        return [a, b]
    W, H = die_wh
    xs = sorted({a[0], b[0]} | {v for r in boxes for v in (r[0], r[2]) if 0 <= v <= W})
    ys = sorted({a[1], b[1]} | {v for r in boxes for v in (r[1], r[3]) if 0 <= v <= H})
    free = {(i,j) for i,x in enumerate(xs) for j,y in enumerate(ys)
            if not any(inside((x,y),r) for r in boxes)}
    src, dst = (xs.index(a[0]),ys.index(a[1])), (xs.index(b[0]),ys.index(b[1]))
    pq = [(0.0,0,src)]; dist={src:(0.0,0)}; parent={}
    while pq:
        length, hops, u = heapq.heappop(pq)
        if dist[u] != (length,hops):
            continue
        if u == dst:
            break
        for di,dj in ((1,0),(-1,0),(0,1),(0,-1)):
            v=(u[0]+di,u[1]+dj)
            if v not in free:
                continue
            p,q=(xs[u[0]],ys[u[1]]),(xs[v[0]],ys[v[1]])
            if any(intersects(p,q,r) for r in boxes):
                continue
            cost=(length+abs(p[0]-q[0])+abs(p[1]-q[1]),hops+1)
            if cost < dist.get(v,(math.inf,math.inf)):
                dist[v]=cost;parent[v]=u;heapq.heappush(pq,(*cost,v))
    if dst not in dist:
        raise ValueError(f'no clock corridor between {a} and {b}')
    pts=[];v=dst
    while True:
        pts.append((xs[v[0]],ys[v[1]]))
        if v==src:break
        v=parent[v]
    pts.reverse()
    # Drop collinear visibility vertices; preserve physical bends.
    out=[]
    for p in pts:
        if len(out)>=2 and ((out[-2][0]==out[-1][0]==p[0]) or (out[-2][1]==out[-1][1]==p[1])):
            out[-1]=p
        else:out.append(p)
    return out


def detour_segments(segments, domain_rects, die_wh, clear_um=8.64):
    """[(x0,y0,x1,y1,level,layer)] -> (segments, endpoint_map, report).

    Report includes per-edge old/new lengths for subsequent physical balancing.
    No endpoint is dropped and input order/tree parent relationships are kept.
    """
    W,H=die_wh
    boxes=[(max(-clear_um,x0-clear_um),max(-clear_um,y0-clear_um),
            min(W+clear_um,x1+clear_um),min(H+clear_um,y1+clear_um))
           for x0,y0,x1,y1 in domain_rects]
    endpoints={tuple(s[i:i+2]) for s in segments for i in (0,2)}
    moved={p:p for p in endpoints if not any(inside(p,r) for r in boxes)}
    for p in sorted(endpoints - moved.keys()):
        moved[p]=legalize(p,boxes,die_wh,taken=moved.values(),separation=clear_um)
    out=[];rows=[]
    for index,s in enumerate(segments):
        a,b=tuple(s[:2]),tuple(s[2:4]);pts=route(moved[a],moved[b],boxes,die_wh)
        length=0
        for p,q in zip(pts,pts[1:]):
            out.append((*p,*q,s[4],'M8' if p[1]==q[1] else 'M9'))
            length+=abs(p[0]-q[0])+abs(p[1]-q[1])
        old=abs(a[0]-b[0])+abs(a[1]-b[1])
        if pts != [a,b]:
            rows.append(dict(edge=index,old_um=round(old,3),new_um=round(length,3),
                             delta_um=round(length-old,3),path=[list(p) for p in pts]))
    # Separate logical nodes must never collapse: this could create a clock loop
    # or merge branches whose independent RC was priced by the original tree.
    reverse={}
    for p,q in moved.items():
        if q in reverse and reverse[q]!=p:
            raise ValueError(f'clock endpoints {p} and {reverse[q]} collapse at {q}; replan branch sites')
        reverse[q]=p
    return out,moved,dict(clear_um=clear_um,changed_edges=len(rows),input_edges=len(segments),
                         output_segments=len(out),moved_endpoints=sum(p!=q for p,q in moved.items()),
                         wire_delta_um=round(sum(r['delta_um'] for r in rows),3),edges=rows,
                         timing='NOT_RUN: rebalance using actual detoured lengths before STA')
