"""Plan-only rooted branch RC with directional layers and horizontal obstacles.

An explicit rectilinear MST joins original physical terminal points. Each edge
uses a valid V-H-V channel; all downstream sink and wire C loads shared edges.
Overlapping edge paths are intentionally not merged: this is a conservative
unmerged-tree prototype, not an extracted Steiner topology or qualification.
No timing measurement or routed geometry is an input.
"""
import math


def channel_path(a,b,obstacles=(),clearance=0.,vertical_obstacles=()):
    xs={a[0],b[0]};ys={a[1],b[1]}
    for r in [*obstacles,*vertical_obstacles]:
        xs.update((r[0]-clearance,r[2]+clearance));ys.update((r[1]-clearance,r[3]+clearance))
    def clear(p,q):
        if p[1]==q[1]:
            lo,hi=sorted((p[0],q[0]))
            return all(not (lo<r[2]+clearance and hi>r[0]-clearance and r[1]-clearance<p[1]<r[3]+clearance) for r in obstacles)
        lo,hi=sorted((p[1],q[1]))
        return all(not (lo<r[3]+clearance and hi>r[1]-clearance and r[0]-clearance<p[0]<r[2]+clearance) for r in vertical_obstacles)
    candidates=[]
    for y in sorted(ys):candidates.append([a,(a[0],y),(b[0],y),b])
    for x in sorted(xs):candidates.append([a,(x,a[1]),(x,b[1]),b])
    good=[p for p in candidates if all(clear(x,y) for x,y in zip(p,p[1:]))]
    if not good:raise ValueError('no valid two-bend channel; requires richer planned routing topology')
    def length(p):return sum(abs(x[0]-y[0])+abs(x[1]-y[1]) for x,y in zip(p,p[1:]))
    path=min(good,key=lambda p:(length(p),p))
    return [(abs(p[0]-q[0])+abs(p[1]-q[1]),'horizontal' if p[1]==q[1] else 'vertical') for p,q in zip(path,path[1:])]


def rooted_rc(points,caps,horizontal_rc,vertical_rc,obstacles=(),clearance=0.,vertical_obstacles=()):
    """points[0] is driver; caps supplies every target in points[1:].

    Per-layer RC=(kohm/um,fF/um) must already reflect that layer's width rule.
    Obstacles are declared separately for each directional layer. A missing
    valid two-bend channel fails closed; it never ignores an obstruction.
    """
    if len(caps)!=len(points)-1:raise ValueError('every physical target needs a cap')
    for v in [*caps,*horizontal_rc,*vertical_rc,clearance]:
        if not math.isfinite(v) or v<0:raise ValueError('invalid physical RC input')
    n=len(points);parent=[-1]*n;paths=[None]*n;used={0};order=[0]
    distances={};routes={}
    for i in range(n):
        for j in range(i+1,n):
            route=channel_path(points[i],points[j],obstacles,clearance,vertical_obstacles)
            distances[i,j]=sum(v for v,_ in route);routes[i,j]=route
    while len(used)<n:
        _,i,j=min((distances[min(i,j),max(i,j)],i,j) for i in sorted(used) for j in range(n) if j not in used)
        parent[j]=i;paths[j]=routes[i,j] if i<j else list(reversed(routes[j,i]));used.add(j);order.append(j)
    edge_r=[0.]*n;edge_c=[0.]*n;intrinsic=[0.]*n
    for j in order[1:]:
        rc=[(length*(horizontal_rc if axis=='horizontal' else vertical_rc)[0],length*(horizontal_rc if axis=='horizontal' else vertical_rc)[1]) for length,axis in paths[j]]
        edge_r[j]=sum(r for r,c in rc);edge_c[j]=sum(c for r,c in rc)
        intrinsic[j]=sum(r*(c/2+sum(C for R,C in rc[k+1:])) for k,(r,c) in enumerate(rc))
    subtree=[0.]+list(caps)
    for j in reversed(order[1:]):subtree[parent[j]]+=subtree[j]+edge_c[j]
    arrival=[0.]*n
    for j in order[1:]:arrival[j]=arrival[parent[j]]+edge_r[j]*subtree[j]+intrinsic[j]
    return dict(target_elmore_ps=arrival[1:],wire_cap_ff=sum(edge_c),total_load_ff=subtree[0],
                wire_um=sum(sum(v for v,_ in p) for p in paths[1:]),parent=parent,
                paths=paths,basis='PLAN rooted directional MST; shared downstream C; unmerged channel-path upper bound, no vias/coupling/capacity qualification')
