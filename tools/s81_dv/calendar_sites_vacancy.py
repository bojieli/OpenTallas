"""Atomically allocate entire serial calendars from legal street vacancies.

The candidate graph covers the endpoint reach diamonds rather than assuming a
rectangular patch of free space. This fits long calendars into narrow streets.
All station counts, graph connections, reach and clock regions are unchanged.
"""
import math


def reserve(st,parent,kids,terms,planned,loc,placer,reach,box_of,explicit=()):
    hop=lambda a,b:abs(a[0]-b[0])+abs(a[1]-b[1])
    same=lambda a,b:hop(planned[a],planned[b])<1e-4
    fixed={};failures=[];groups=[];seen=set();R=reach-6.0
    for v in sorted(explicit):
        c=planned[v];w,h=loc[v][2:4];b=box_of.get(v)
        rect=(c[0]-w/2,c[1]-h/2,c[0]+w/2,c[1]+h/2)
        if placer.hits(rect) or (b and not(b[0]<=c[0]<=b[2] and b[1]<=c[1]<=b[3])):
            raise ValueError('illegal explicit calendar macro: '+str((v,c,rect,b)))
        placer.add(rect);fixed[v]=c
    for v in sorted(st):
        if v in seen or (v in parent and len(kids[parent[v]])==1 and same(v,parent[v])):continue
        chain=[v]
        while len(kids[chain[-1]])==1:
            u=kids[chain[-1]][0]
            if not same(u,chain[-1]):break
            chain.append(u)
        seen.update(chain)
        if len(chain)>=4 and not any(u in fixed for u in chain):groups.append(chain)
    # Place the longest calendars first, with constrained endpoint intersections
    # deciding which legal street nodes are available for the entire path.
    groups.sort(key=lambda c:(-len(c),c[0]))
    for chain in groups:
        chain_set=set(chain);w=max(loc[v][2] for v in chain);h=max(loc[v][3] for v in chain)
        external=[]
        for v in chain:
            if v in parent and parent[v] not in chain_set:external.append(fixed.get(parent[v],planned[parent[v]]))
            external.extend(fixed.get(u,planned[u]) for u in kids[v] if u not in chain_set)
            external.extend(terms[v])
        anchor=planned[chain[0]]
        # A graph vertex is a whole legal macro site. Grid pitch guarantees
        # mutual clearance; filter every vertex through all endpoint diamonds.
        sx,sy=w+1.0,h+1.0
        lo_x,hi_x=anchor[0]-R,anchor[0]+R
        lo_y,hi_y=anchor[1]-R,anchor[1]+R
        for v in chain:
            if v in box_of:
                b=box_of[v];lo_x=max(lo_x,b[0]);lo_y=max(lo_y,b[1]);hi_x=min(hi_x,b[2]);hi_y=min(hi_y,b[3])
        points=[]
        for ix in range(math.ceil((lo_x-anchor[0])/sx),math.floor((hi_x-anchor[0])/sx)+1):
            for iy in range(math.ceil((lo_y-anchor[1])/sy),math.floor((hi_y-anchor[1])/sy)+1):
                c=(anchor[0]+ix*sx,anchor[1]+iy*sy)
                if hop(c,anchor)>R or any(hop(c,p)>R for p in external):continue
                if not placer.hits((c[0]-w/2,c[1]-h/2,c[0]+w/2,c[1]+h/2)):points.append(c)
        if len(points)<len(chain):
            failures.append(dict(first=chain[0],stages=len(chain),free_vertices=len(points),cause='insufficient legal endpoint-diamond capacity'));continue
        starts=sorted(points,key=lambda c:(hop(c,anchor),c))[:4]
        best=None
        for start in starts:
            remaining=set(points);remaining.remove(start);path=[start]
            while len(path)<len(chain):
                c=min(remaining,key=lambda q:(hop(q,path[-1]),hop(q,anchor),q))
                if hop(c,path[-1])>R:break
                path.append(c);remaining.remove(c)
            if len(path)==len(chain):
                score=sum(hop(c,anchor) for c in path)
                if best is None or score<best[0]:best=score,path
        if best is None:
            failures.append(dict(first=chain[0],stages=len(chain),free_vertices=len(points),cause='vacancy components cannot form a complete bounded-hop path'));continue
        for v,c in zip(chain,best[1]):
            vw,vh=loc[v][2:4];placer.add((c[0]-vw/2,c[1]-vh/2,c[0]+vw/2,c[1]+vh/2));fixed[v]=c
    return fixed,dict(groups=len(groups),reserved_stations=len(fixed),unresolved=failures,
        rule='atomic whole serial calendar paths on legal vacancy vertices inside all endpoint reach diamonds and own clock region')
