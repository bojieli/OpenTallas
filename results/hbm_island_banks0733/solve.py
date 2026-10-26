"""Bounded proposal only: move existing indexed FT cells around a clock island."""
import copy,gzip,json,math
from pathlib import Path
B=Path(__file__).parent
P=json.load(gzip.open(B/'export.json.gz','rt'))

def hit(a,b):return min(a[2],b[2])-max(a[0],b[0])>1e-6 and min(a[3],b[3])-max(a[1],b[1])>1e-6
def route(a,b,isl):
    options=[[a,(b[0],a[1]),b],[a,(a[0],b[1]),b]]
    for x in [isl[0]-.108,isl[2]+.108]:options.append([a,(x,a[1]),(x,b[1]),b])
    for y in [isl[1]-.27,isl[3]+.27]:options.append([a,(a[0],y),(b[0],y),b])
    legal=[]
    for pts in options:
        blocked=False
        for u,v in zip(pts,pts[1:]):
            if abs(u[0]-v[0])<1e-6:
                blocked |= isl[0]+1e-6<u[0]<isl[2]-1e-6 and min(max(u[1],v[1]),isl[3])-max(min(u[1],v[1]),isl[1])>1e-6
            else:
                blocked |= isl[1]+1e-6<u[1]<isl[3]-1e-6 and min(max(u[0],v[0]),isl[2])-max(min(u[0],v[0]),isl[0])>1e-6
        if not blocked:legal.append(sum(abs(u[0]-v[0])+abs(u[1]-v[1]) for u,v in zip(pts,pts[1:])))
    return min(legal) if legal else float('inf')

def keys(r):
    return [(x,y) for x in range(math.floor(r[0]/2.16),math.floor((r[2]-1e-6)/2.16)+1)
            for y in range(math.floor(r[1]/.27+1e-6),math.floor((r[3]-1e-6)/.27)+1)]

report=dict(source_sha256=P['sha256'],qualification='PROPOSAL ONLY; no source plan edited; full routing/PG/capacity/internal stations NOT RUN',types={},moves=[])
for tn,t in P['types'].items():
    isl=t['island'];s=next(s for s in t['ft_slots'] if s['name']==t['target']);cw,ch=s['bit_site_cell_um']
    pins={(b,i):(x,y) for b,i,l,x,y,f in t['pins']};occ={};bad=[]
    for st in t['ft_slots']:
        w,h=st.get('bit_site_cell_um',[1.404,.27])
        for gi,g in enumerate(st.get('bit_sites_um',[])):
            for bit,(x,y) in enumerate(g):
                r=(x,y,x+w,y+h)
                if st is s and hit(r,isl):bad.append((gi,bit));continue
                for k in keys(r):occ.setdefault(k,[]).append(r)
    unresolved=[]
    for gi,bit in bad:
        x,y=s['bit_sites_um'][gi][bit]
        a=(s['bit_sites_um'][gi-1][bit][0]+.54,s['bit_sites_um'][gi-1][bit][1]+.135) if gi else pins[s['name']+'_i',bit]
        b=(s['bit_sites_um'][gi+1][bit][0]+.54,s['bit_sites_um'][gi+1][bit][1]+.135) if gi+1<len(s['bit_sites_um']) else pins[s['name']+'_o',bit]
        ys={round(y+k*.27,6) for k in range(-85,86)}
        xs={x}
        for k in range(12):
            xs.add(round((math.floor((isl[0]-cw)/.108)-14*k)*.108,6))
            xs.add(round((math.ceil(isl[2]/.108)+14*k)*.108,6))
        candidates=sorted(((xx,yy) for xx in xs for yy in ys),key=lambda q:(abs(q[0]-x)+abs(q[1]-y),q[1],q[0]))
        found=None
        for xx,yy in candidates:
            r=(xx,yy,xx+cw,yy+ch)
            if xx<0 or yy<0 or r[2]>t['outline_um'][0] or r[3]>t['outline_um'][1] or hit(r,isl):continue
            if any(hit(r,c[:4]) for c in t['cores']):continue
            if any(hit(r,o) for k in keys(r) for o in occ.get(k,[])):continue
            c=(xx+.54,yy+.135)
            if max(route(a,c,isl),route(c,b,isl))>405+1e-6:continue
            found=(xx,yy,r);break
        if found is None:unresolved.append(dict(group=gi,bit=bit));continue
        xx,yy,r=found;s['bit_sites_um'][gi][bit]=[xx,yy]
        for k in keys(r):occ.setdefault(k,[]).append(r)
        report['moves'].append(dict(type=tn,slot=s['name'],group=gi,bit=bit,old=[x,y],new=[xx,yy],displacement_um=abs(xx-x)+abs(yy-y)))
    remaining=sum(hit((x,y,x+cw,y+ch),isl) for g in s['bit_sites_um'] for x,y in g)
    over=[];maximum=0.
    for bit in range(len(s['bit_sites_um'][0])):
        chain=[pins[s['name']+'_i',bit]]+[(g[bit][0]+.54,g[bit][1]+.135) for g in s['bit_sites_um']]+[pins[s['name']+'_o',bit]]
        for leg,(a,b) in enumerate(zip(chain,chain[1:])):
            dist=route(a,b,isl);maximum=max(maximum,dist)
            if dist>405+1e-6:over.append([bit,leg,dist])
    report['types'][tn]=dict(initial_illegal_cells=len(bad),remaining_illegal_cells=remaining,unresolved=unresolved,
        max_island_avoiding_hop_um=maximum,over_reach_or_blocked_hops=len(over),examples=over[:8],
        unmodeled_internal_stations=t['unmodeled_internal_stations'],bits=len(s['bit_sites_um'][0]),stages=len(s['bit_sites_um']))
report['verdict']='PASS_PROPOSAL' if all(not v['remaining_illegal_cells'] and not v['over_reach_or_blocked_hops'] for v in report['types'].values()) else 'PARTIAL_PROPOSAL'
report['added_cycles']=0;report['added_cells']=0
(B/'proposal.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k!='moves'},indent=1))
print('moved',len(report['moves']),'max displacement',max((m['displacement_um'] for m in report['moves']),default=0))
