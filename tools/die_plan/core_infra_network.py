"""Merge planned rectilinear conductors and solve passive RC first moments.

Horizontal/vertical wires occupy distinct layers. Colinear overlap is counted
once. Layers connect only at declared path turns or terminal access points;
other orthogonal crossings do not acquire an invented via. Declared vias have
zero R/C in this prototype and must be qualified separately before build.
"""
from collections import defaultdict


def merged_rc(points,caps,polylines,horizontal_rc,vertical_rc):
    import numpy as np
    def point(p):return tuple(round(float(v),9) for v in p)
    points=list(map(point,points));paths=[list(map(point,p)) for p in polylines]
    lines=defaultdict(list);ties=set(points);raw_length=0.
    for path in paths:
        ties.update(path[1:-1])
        for a,b in zip(path,path[1:]):
            if a==b:continue
            axis='H' if a[1]==b[1] else 'V'
            if axis=='V' and a[0]!=b[0]:raise ValueError('non-rectilinear planned wire')
            constant=a[1] if axis=='H' else a[0];lo,hi=sorted((a[0],b[0]) if axis=='H' else (a[1],b[1]))
            lines[axis,constant].append((lo,hi));raw_length+=hi-lo
    parent={}
    def add(k):parent.setdefault(k,k);return k
    def find(k):
        if parent[k]!=k:parent[k]=find(parent[k])
        return parent[k]
    def join(a,b):
        a,b=find(a),find(b)
        if a!=b:parent[max(a,b)]=min(a,b)
    def node(axis,fixed,v):return add((axis,round(v,9),fixed) if axis=='H' else (axis,fixed,round(v,9)))
    edges=[];segments=[]
    for (axis,fixed),intervals in sorted(lines.items()):
        cuts={v for pair in intervals for v in pair}
        cuts.update(p[0] if axis=='H' else p[1] for p in ties if (p[1] if axis=='H' else p[0])==fixed)
        cuts=sorted(cuts)
        for lo,hi in zip(cuts,cuts[1:]):
            mid=(lo+hi)/2
            if not any(a<=mid<=b for a,b in intervals):continue
            a,b=node(axis,fixed,lo),node(axis,fixed,hi);r,c=horizontal_rc if axis=='H' else vertical_rc;length=hi-lo
            edges.append((a,b,length*r,length*c));segments.append(dict(axis=axis,a=list(a[1:]),b=list(b[1:]),length_um=length))
    for x,y in sorted(ties):
        h,v=('H',x,y),('V',x,y)
        if h in parent and v in parent:join(h,v)
    for a,b,r,c in edges:
        if r==0:join(a,b)
    terminals=[]
    for x,y in points:
        keys=[k for k in [('H',x,y),('V',x,y)] if k in parent]
        terminals.append(find(keys[0]) if keys else add(('H',x,y)))
    root=find(terminals[0]);vertices=sorted({find(k) for k in parent});unknown=[k for k in vertices if k!=root];index={k:i for i,k in enumerate(unknown)};n=len(unknown)
    G=np.zeros((n,n));wire=np.zeros(n);total_wire_c=0.;physical_edges=0
    for a,b,r,c in edges:
        a,b=find(a),find(b);total_wire_c+=c
        for k in (a,b):
            if k!=root:wire[index[k]]+=c/2
        if a==b:continue
        physical_edges+=1
        g=1/r
        if a!=root:G[index[a],index[a]]+=g
        if b!=root:G[index[b],index[b]]+=g
        if a!=root and b!=root:G[index[a],index[b]]-=g;G[index[b],index[a]]-=g
    rhs=np.zeros((n,1+len(caps)))
    if n:rhs[:,0]=wire
    for j,k in enumerate(terminals[1:]):
        k=find(k)
        if k!=root:rhs[index[k],j+1]+=1
    solution=np.linalg.solve(G,rhs) if n else rhs
    coeff=[];wire_arr=[]
    for k in terminals[1:]:
        k=find(k);row=solution[index[k]] if k!=root else np.zeros(1+len(caps));wire_arr.append(float(row[0]));coeff.append([float(v) for v in row[1:]])
    arrivals=[w+sum(r*c for r,c in zip(row,caps)) for w,row in zip(wire_arr,coeff)]
    union_length=sum(s['length_um'] for s in segments)
    return dict(target_elmore_ps=arrivals,pin_elmore_coeff_kohm=coeff,wire_elmore_ps=wire_arr,
                wire_cap_ff=total_wire_c,total_load_ff=total_wire_c+sum(caps),wire_um=union_length,
                original_tree_wire_um=raw_length,overlap_removed_um=raw_length-union_length,
                overlap_removed_fraction=(raw_length-union_length)/raw_length if raw_length else 0.,
                network_nodes=len(vertices),network_edges=physical_edges,network_cycles=physical_edges-len(vertices)+1,
                merged_segments=segments,basis='Merged planned directional-layer conductor union + conductance RC first moment; shared C once and parallel R solved; zero-R/C declared vias, no coupling/capacity qualification')
