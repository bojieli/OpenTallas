"""DIE-HBM-11 estimate-before-build for the 40 UNPLANNED crossing pairs (C25c sourcefix census).
usage: missing_lane_estimate.py die_plan.json unplanned_sourcefix_census.json OUT.json
Read-only. Face supply = face length minus union of existing port windows on that face (die coords);
demand = missing bits / budgets.face_pins_per_um on every crossing of the chosen path.
Path = existing lane ports between src and dst (lane whose first src and last dst match), else UNPATHED.
ESTIMATE only: no track/occupancy census inside partitions, no route, no timing."""
import json,sys,collections
P=json.load(open(sys.argv[1]));C=json.load(open(sys.argv[2]))
B=P['budgets'];dens=B['face_pins_per_um']
parts={p['name']:p for p in P['partitions']};T=P['partition_types']
def box(n):
    p=parts[n];w,h=T[p['type']]['outline_um'][:2]
    if p.get('orient','R0') in ('R90','R270','MXR90','MYR90'):w,h=h,w
    x,y=p['origin_um'];return (x,y,x+w,y+h)
def shared(a,b,tol=0.6):
    A,Bx=box(a),box(b)
    if abs(A[2]-Bx[0])<tol or abs(Bx[2]-A[0])<tol:
        lo,hi=max(A[1],Bx[1]),min(A[3],Bx[3]);return ('V',round(A[2] if abs(A[2]-Bx[0])<tol else A[0],3)),max(0,hi-lo)
    if abs(A[3]-Bx[1])<tol or abs(Bx[3]-A[1])<tol:
        lo,hi=max(A[0],Bx[0]),min(A[2],Bx[2]);return ('H',round(A[3] if abs(A[3]-Bx[1])<tol else A[1],3)),max(0,hi-lo)
    return None,0
ports={p['id']:p for p in P['ports']}
edge_dem=collections.Counter();edge_len={}
for p in P['ports']:
    k=frozenset((p['src']['part'],p['dst']['part']));e,L=shared(*k) if len(k)==2 else (None,0)
    edge_len[k]=L;edge_dem[k]+=p['width']
lat=P['latency']['lanes']
lanes=[]
for l in P['lanes']:
    ps=[ports[i] for i in l['ports']]
    lanes.append((l['id'],ps[0]['src']['part'],ps[-1]['dst']['part'],ps))
rows=[];extra=collections.defaultdict(float)
for pr in C['pairs']:
    s,d,bits=pr['src'],pr['dst'],pr['bits']
    cand=[x for x in lanes if x[1]==s and x[2]==d]
    if not cand:
        a,b=box(s),box(d)
        gap=max(0,max(a[0],b[0])-min(a[2],b[2]))+max(0,max(a[1],b[1])-min(a[3],b[3]))
        rows.append(dict(src=s,dst=d,bits=bits,path='UNPATHED',box_gap_um=round(gap,2),drivers=pr['drivers']));continue
    lid,_,_,ps=max(cand,key=lambda x:sum(p['width'] for p in x[3]))
    cr=[]
    for p in ps:
        k=frozenset((p['src']['part'],p['dst']['part']));extra[k]+=bits
        cr.append(dict(port=p['id'],src=p['src']['part'],dst=p['dst']['part'],width=p['width'],shared_um=round(edge_len[k],2)))
    rows.append(dict(src=s,dst=d,bits=bits,path=lid,cycles=lat.get(lid,{}).get('cycles'),stations=lat.get(lid,{}).get('stations'),crossings=cr,drivers=pr['drivers']))
faces=[]
for k,add in sorted(extra.items(),key=lambda x:-x[1]):
    L=edge_len[k];sup=L*dens;now=edge_dem[k]
    faces.append(dict(edge=sorted(k),shared_um=round(L,2),supply_pins=round(sup),demand_now=now,add=add,util_after=round((now+add)/max(sup,1e-9),3),fits=now+add<=sup))
out=dict(status='ESTIMATE (UNCHECKED, read-only)',density_pins_per_um=dens,total_bits=sum(r['bits'] for r in rows),
    unpathed=[r for r in rows if r['path']=='UNPATHED'],faces=faces,pairs=rows)
json.dump(out,open(sys.argv[3],'w'),indent=1)
print('total',out['total_bits'],'unpathed',[(r['src'],r['dst'],r['bits'],r['box_gap_um']) for r in out['unpathed']])
for f in faces[:25]:print(f)
# --- unpathed pairs: shortest abutment path (BFS over partitions sharing >=20 um edge; hard-core-only types excluded = none here)
import heapq
names=list(parts);adj=collections.defaultdict(list)
for i,a in enumerate(names):
    for b in names[i+1:]:
        e,L=shared(a,b)
        if L>=20:adj[a].append(b);adj[b].append(a)
def ctr(n):
    x0,y0,x1,y1=box(n);return ((x0+x1)/2,(y0+y1)/2)
def path(s,d):
    D={s:0};prev={};h=[(0,s)]
    while h:
        c,u=heapq.heappop(h)
        if u==d:break
        if c>D[u]:continue
        for v in adj[u]:
            w=abs(ctr(u)[0]-ctr(v)[0])+abs(ctr(u)[1]-ctr(v)[1])
            if c+w<D.get(v,1e18):D[v]=c+w;prev[v]=u;heapq.heappush(h,(c+w,v))
    if d not in D:return None,None
    p=[d]
    while p[-1]!=s:p.append(prev[p[-1]])
    return p[::-1],D[d]
smax=B['ft_station_max_um'];prop=[]
for r in out['unpathed']:
    p,L=path(r['src'],r['dst'])
    edges=[]
    for a,b in zip(p,p[1:]):
        k=frozenset((a,b));edges.append(dict(edge=[a,b],shared_um=round(edge_len.get(k,shared(a,b)[1]),2),demand_now=edge_dem.get(k,0),util_after=round((edge_dem.get(k,0)+r['bits']+extra.get(k,0))/max(1,shared(a,b)[1]*dens),3)))
    r.update(bfs_path=p,centre_manhattan_um=round(L,1),stations_est=max(0,int(-(-L//smax))-1),edges=edges)
    prop.append((r['src'],r['dst'],r['bits'],len(p)-1,round(L),r['stations_est'],max(e['util_after'] for e in edges)))
json.dump(out,open(sys.argv[3],'w'),indent=1)
print('UNPATHED proposals (src,dst,bits,hops,centre_um,stations_est,max_edge_util):')
for x in prop:print(x)
