import json,re,sys
plan,rep=sys.argv[1],sys.argv[2]
d=json.load(open(plan)); r=json.load(open(rep))
T=d['partition_types']; P={}
for p in d['partitions']:
    t=T[p['type']] if p['type'] in T else None
    w,h=t['outline_um'] if t else (0,0)
    if p.get('orient','R0') in ('R90','R270','MXR90','MYR90'): w,h=h,w
    x,y=p['origin_um']; P[p['name']]=(x,y,x+w,y+h,p['type'],t.get('hard') if t else None)
# root is not a partition maybe
def gap(a,b):
    if a not in P or b not in P: return None
    ax0,ay0,ax1,ay1=P[a][:4]; bx0,by0,bx1,by1=P[b][:4]
    dx=max(0,bx0-ax1,ax0-bx1); dy=max(0,by0-ay1,ay0-by1); return round(dx+dy,1)
def cdist(a,b):
    if a not in P or b not in P: return None
    ax=(P[a][0]+P[a][2])/2; ay=(P[a][1]+P[a][3])/2; bx=(P[b][0]+P[b][2])/2; by=(P[b][1]+P[b][3])/2
    return round(abs(ax-bx)+abs(ay-by),1)
# lanes per (src,dst) partition pair in plan (direct port hops)
direct={}
for po in d['ports']:
    k=(po['src']['part'],po['dst']['part']); direct[k]=direct.get(k,0)+po['width']
rows=[]
for e in r['errors']:
    m=re.match(r'\s*UNPLANNED (\S+) -> (\S+): (\d+) .*\((\d+) b planned',e)
    if not m: print('??',e); continue
    s,t,b,pl=m.group(1),m.group(2),int(m.group(3)),int(m.group(4))
    rows.append((s,t,b,pl,gap(s,t),cdist(s,t),direct.get((s,t),0),direct.get((t,s),0)))
print('src\tdst\tbits\tplanned_direct_lanes\tedge_gap_um\tcentre_manh_um\tport_hop_bits_st\tport_hop_bits_ts')
for x in sorted(rows,key=lambda x:-x[2]): print('\t'.join(map(str,x)))
print('#parts missing:', sorted({n for x in rows for n in x[:2] if n not in P}))
