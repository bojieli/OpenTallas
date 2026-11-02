"""Obstacle-aware rectilinear native clock planning tree, not routed metal."""
import json,pathlib,heapq,math
R=pathlib.Path(__file__).parent
M=json.loads((R/'clock_model.json').read_text()); P=json.loads((R/'input/model.json').read_text())
G=json.loads((R/'input/clock_entry_gate.json').read_text())
W,H=M['outline_um']; roots=[tuple(q['xy_um']) for q in M['roots']]; src=tuple(G['declared_points']['clk'])
blocks=[[a-4.368,b-4.368,c+4.368,d+4.368] for a,b,c,d in (m['rect_um'] for m in P['macros'])]
xs=sorted(set([src[0]]+[p[0] for p in roots]+[v for b in blocks for v in (b[0],b[2]) if 4.32<=v<=W-4.32]))
ys=sorted(set([src[1]]+[p[1] for p in roots]+[v for b in blocks for v in (b[1],b[3]) if 4.32<=v<=H-4.32]))
def open_segment(p,q):
    a,b=min(p[0],q[0]),min(p[1],q[1]);c,d=max(p[0],q[0]),max(p[1],q[1])
    return not any(c>x+1e-8 and a<z-1e-8 and d>y+1e-8 and b<t-1e-8 for x,y,z,t in blocks)
nx=len(xs);ny=len(ys)
start=ys.index(src[1])*nx+xs.index(src[0]); dist={start:0};prev={};pending=[(0,start)]
while pending:
    d,n=heapq.heappop(pending)
    if d!=dist[n]: continue
    x,y=n%nx,n//nx;p=(xs[x],ys[y])
    for xx,yy in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
        if not(0<=xx<nx and 0<=yy<ny):continue
        q=(xs[xx],ys[yy]); nn=yy*nx+xx
        nd=d+abs(q[0]-p[0])+abs(q[1]-p[1])
        if nd<dist.get(nn,math.inf)-1e-9 and open_segment(p,q):
            dist[nn]=nd;prev[nn]=n;heapq.heappush(pending,(nd,nn))
edges=set();paths=[]
for r in roots:
    n=ys.index(r[1])*nx+xs.index(r[0]);assert n in dist,('unreachable regional root',r)
    length=dist[n];path=[]
    while n!=start:
        p=prev[n]; edges.add((p,n));path.append([xs[n%nx],ys[n//nx]]);n=p
    path.append(list(src));paths.append(dict(regional_root=r,street_path_um=path[::-1],length_um=length))
wire=sum(abs(xs[a%nx]-xs[b%nx])+abs(ys[a//nx]-ys[b//nx]) for a,b in edges)
out=dict(status='DISABLED_NATIVE_STREET_TREE_PREP',root=list(src),regional_count=len(roots),macro_halo_um=4.32,planning_wire_envelope_width_um=.096,unique_street_tree_length_um=wire,min_root_to_region_um=min(q['length_um'] for q in paths),max_root_to_region_um=max(q['length_um'] for q in paths),paths=paths,tree_edges_um=[[[xs[a%nx],ys[a//nx]],[xs[b%nx],ys[b//nx]]] for a,b in sorted(edges)],note='Acyclic shared shortest-path street skeleton. This quantifies actual spatial buffering/balance demand, not an inserted/equal-latency CTS tree. CTS must add electrical repeaters/branches and balance arrival within unchanged TT250/FF202.5 budgets. No public-clock event.',held=['Actual electrical CTS fanout/buffer count/RC/delay/skew','Actual PG connectivity of inserted cells','Actual native source/parent reset and START joins'])
(R/'spine_model.json').write_text(json.dumps(out,indent=2))
print(json.dumps({k:v for k,v in out.items() if k not in ('paths','tree_edges_um')},indent=2))
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
fig,ax=plt.subplots(figsize=(10,13))
for m in P['macros']:
    a,b,c,d=m['rect_um'];ax.add_patch(Rectangle((a,b),c-a,d-b,facecolor='#ddd',edgecolor='#888',linewidth=.4))
for a,b in out['tree_edges_um']:ax.plot([a[0],b[0]],[a[1],b[1]],color='#225588',linewidth=.65)
ax.scatter([p[0] for p in roots],[p[1] for p in roots],s=13,c='#d34020',label='Regional CTS landing reserves')
ax.scatter(*src,s=90,c='red',marker='*',label='One scalar clk input')
ax.set(xlim=(0,W),ylim=(0,H),aspect='equal',xlabel='um',ylabel='um',title='Programme single-input native clock street tree PREP\nActual source sinks; macro4.32halo + .096 planning wire envelope\nBranch/repeater electrical sizing and balanced TT/FF arrival remain CTS qualification')
ax.legend(fontsize=8);fig.tight_layout();fig.savefig(R/'spine_review.png',dpi=160)
