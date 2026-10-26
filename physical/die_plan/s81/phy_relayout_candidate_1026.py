#!/usr/bin/env python3
"""Same-area 14-link S81 perimeter candidate, geometry and hop lower bounds only.

This does not emit a connected die_plan. Changed port paths must be rebuilt with
<=405-um registered stations and priced before G0C/bind/trial/route can pass.
"""
import argparse
import copy
import json
import math
import heapq
from pathlib import Path

G, X0, PX, PY = 8.64, 103.68, 1442.88, 1226.88
SHORE, DEPTH, GUARD = 3318.0, 1013.0, 63.64
SLOT = math.ceil((SHORE + 2*GUARD)/G)*G


def overlap(a,b):
    return max(0,min(a[2],b[2])-max(a[0],b[0]))*max(0,min(a[3],b[3])-max(a[1],b[1]))


def candidate(raw):
    T=raw['partition_types']; P={p['name']:p for p in raw['partitions']}
    old={n:[*p['origin_um'],p['origin_um'][0]+T[p['type']]['outline_um'][0],p['origin_um'][1]+T[p['type']]['outline_um'][1]] for n,p in P.items()}
    rects=copy.deepcopy(old)
    def put(n,x,y,w,h):rects[n]=[round(v,4) for v in (x,y,x+w,y+h)]
    north=['lk_WN2','lk_WN1','lk_WN0','lk_WN3','lk_WS3','lk_EN2','lk_EN0','lk_EN1','lk_EN3']
    for i,n in enumerate(north):put(n,X0+i*SLOT,X0+19*PY,SLOT,PY)
    x=X0
    for n in ('lk_WS2','lk_WS1','lk_WS0'):
        put(n,x,X0,SLOT,PY);x+=SLOT
    for n,w in (('iqf',1200.96),('phy_hbm',6*PX),('eng',PX),('s_7S_x10',PX)):
        put(n,x,X0,w,PY);x+=w
    for n in ('lk_ES0','lk_ES1'):
        put(n,x,X0,SLOT,PY);x+=SLOT
    # Re-home the former north station into the available SE cell. Its old cell
    # and row18/c12 free cell now host compact BK near its original north home.
    put('s_4N_x06',x,X0,PX,PY)
    put('bk_sel',X0+11*PX,X0+18*PY,2*PX,PY)
    # The second cell of the old tall WS3 partition becomes the compact gunit.
    put('gunit',X0+6*PX,X0+PY,PX,PY)
    changed={n:dict(before=old[n],after=r) for n,r in rects.items() if any(abs(a-b)>1e-4 for a,b in zip(r,old[n]))}
    conflicts=[]
    names=list(rects)
    for i,a in enumerate(names):
        for b in names[i+1:]:
            area=overlap(rects[a],rects[b])
            if area>1e-3:conflicts.append(dict(a=a,b=b,area_um2=round(area,3)))
    W,H=raw['die']['outline_um']
    outside=[n for n,r in rects.items() if r[0]<X0-1e-6 or r[1]<X0-1e-6 or r[2]>W-X0+1e-6 or r[3]>H-X0+1e-6]
    macros=[]
    for n in north+['lk_WS2','lk_WS1','lk_WS0','lk_ES0','lk_ES1']:
        r=rects[n];side='N' if n in north else 'S'
        m=[r[0]+GUARD,r[3]-DEPTH if side=='N' else r[1],r[0]+GUARD+SHORE,r[3] if side=='N' else r[1]+DEPTH]
        macros.append(dict(part=n,side=side,partition_um=r,macro_um=m,area_mm2=round(SHORE*DEPTH/1e6,6),power_w=4.37))
    # Same relative gunit hard-core geometry; only the 699.84-um empty left band
    # is removed. Every hard-core-to-hard-core distance is unchanged.
    gu=[]
    for core in T[P['gunit']['type']]['hard_cores']:
        c=copy.deepcopy(core);c['origin_um'][0]=round(c['origin_um'][0]-699.84,4);gu.append(c)
    bk=[]
    for core in T[P['bk_sel']['type']]['hard_cores']:
        c=copy.deepcopy(core);n=c['inst']
        if 'g_q[' in n:
            q=int(n.split('g_q[')[1].split(']')[0]);c['origin_um']=[G+q*(648+G),G]
        elif n.endswith('u_tx'):
            c['origin_um']=[G,665.28];c['outline_um']=[626.4,544.32];c['rebuild_required']=True
        elif n.endswith('u_c'):c['origin_um']=[652.32,665.28]
        elif n.endswith('u_g'):c['origin_um']=[1058.4,665.28]
        bk.append(c)
    packing={}
    for n,cores in (('gunit',gu),('bk_sel',bk)):
        r=rects[n];w,h=r[2]-r[0],r[3]-r[1]
        boxes={c['inst']:[*c['origin_um'],c['origin_um'][0]+c['outline_um'][0],c['origin_um'][1]+c['outline_um'][1]] for c in cores}
        bad=[k for k,b in boxes.items() if b[0]<G-1e-6 or b[1]<G-1e-6 or b[2]>w-G+1e-6 or b[3]>h-G+1e-6]
        collision=[(a,b) for i,a in enumerate(boxes) for b in list(boxes)[i+1:] if overlap(boxes[a],boxes[b])>1e-3]
        packing[n]=dict(outline_um=[w,h],hard_cores=cores,halo_um=G,outside=bad,overlaps=collision)
    ports={p['id']:p for p in raw['ports']}
    def ctr(r):return((r[0]+r[2])/2,(r[1]+r[3])/2)
    def hops(a,b,rs):
        aa,bb=ctr(rs[a]),ctr(rs[b]);return math.ceil((abs(aa[0]-bb[0])+abs(aa[1]-bb[1]))/405)
    bounds=[]
    for lane in raw['lanes']:
        chain=[ports[n] for n in lane['ports']]
        a,b=chain[0]['src']['part'],chain[-1]['dst']['part']
        if any(p[e]['part'] in changed for p in chain for e in ('src','dst')):
            before,after=hops(a,b,old),hops(a,b,rects)
            bounds.append(dict(lane=lane['id'],src=a,dst=b,width=chain[0]['width'],old_center_min_hops=before,new_center_min_hops=after,delta_min_hops=after-before,current_port_crossings=len(chain)))
    # Visibility graph uses actual abutting rectangles. PHY partitions are
    # endpoints only: new large macros cannot be hidden transit corridors.
    adj={n:[] for n in names}
    for i,a in enumerate(names):
        ar=rects[a]
        for b in names[i+1:]:
            br=rects[b];span=0
            if abs(ar[2]-br[0])<1e-3 or abs(br[2]-ar[0])<1e-3:
                span=max(0,min(ar[3],br[3])-max(ar[1],br[1]))
            if abs(ar[3]-br[1])<1e-3 or abs(br[3]-ar[1])<1e-3:
                span=max(span,max(0,min(ar[2],br[2])-max(ar[0],br[0])))
            if span>12:
                ca,cb=ctr(ar),ctr(br);cost=abs(ca[0]-cb[0])+abs(ca[1]-cb[1])
                adj[a].append((b,span,cost));adj[b].append((a,span,cost))
    unreachable=[];skeleton=[];demand={}
    for b in bounds:
        src,dst,width=b['src'],b['dst'],b['width'];heap=[(0,src)];dist={src:0};prev={}
        while heap:
            cost,n=heapq.heappop(heap)
            if cost!=dist[n]:continue
            if n==dst:break
            for nxt,span,step in adj[n]:
                if (nxt.startswith('lk_') or nxt=='phy_hbm') and nxt!=dst:continue
                if nxt.startswith(('fW','fE')) and nxt!=dst and not(rects[nxt][1]<=X0+PY+.01 or rects[nxt][3]>=X0+19*PY-.01):continue
                if width>3.6*(span-12):continue
                nc=cost+step*(4 if n.startswith(('fW','fE')) or nxt.startswith(('fW','fE')) else 1)
                if nc<dist.get(nxt,float('inf')):dist[nxt]=nc;prev[nxt]=(n,span);heapq.heappush(heap,(nc,nxt))
        if dst not in dist:unreachable.append(b['lane']);continue
        path=[dst]
        while path[-1]!=src:
            n=path[-1];par,span=prev[n];key=tuple(sorted((n,par)))
            v=demand.setdefault(key,dict(parts=list(key),face_span_um=round(span,4),affected_bits=0))
            v['affected_bits']+=width;path.append(par)
        path.reverse();length=sum(abs(ctr(rects[a])[0]-ctr(rects[b])[0])+abs(ctr(rects[a])[1]-ctr(rects[b])[1]) for a,b in zip(path,path[1:]))
        skeleton.append(dict(lane=b['lane'],parts=path,centerline_um=round(length,3),route_cost=round(dist[dst],3),min_registered_hops=math.ceil(length/405)))
    cuts=[]
    for v in demand.values():
        v['affected_util_at_60pct_pin_budget']=round(v['affected_bits']/(3.6*(v['face_span_um']-12)),3);cuts.append(v)
    cuts.sort(key=lambda v:v['affected_util_at_60pct_pin_budget'],reverse=True)
    affected_ids={b['lane'] for b in bounds}
    affected_ports={pid for lane in raw['lanes'] if lane['id'] in affected_ids for pid in lane['ports']}
    background={};edge_layers={}
    for p in raw['ports']:
        if p['id'] in affected_ports:continue
        a,b=p['src']['part'],p['dst']['part']
        if a not in rects or b not in rects:continue
        key=tuple(sorted((a,b)));background[key]=background.get(key,0)+p['width']+1
        edge_layers.setdefault(key,set()).update(p['layers'])
    full=[]
    edge_spans={tuple(sorted((a,b))):span for a,neighbours in adj.items() for b,span,cost in neighbours}
    for key in set(background)|set(demand):
        span=edge_spans.get(key)
        if span is None:continue
        add=demand.get(key,{}).get('affected_bits',0);base=background.get(key,0)
        layers=max(2,len(edge_layers.get(key,set())))
        capacity=6*(span-12)*layers/2
        full.append(dict(parts=list(key),span_um=round(span,3),background_bits=base,affected_bits=add,
            total_bits=base+add,layers=layers,full_pin_ratio=round((base+add)/capacity,4)))
    full.sort(key=lambda v:v['full_pin_ratio'],reverse=True)
    return dict(spatial_graph=dict(unreachable_affected_lanes=unreachable,reachable=len(skeleton),routes=skeleton,
        cut_scope='aggregate face-demand planning bounds; local10um pin windows and actualM4-M7 route capacity still require G0C/GRT',cuts=cuts,full_background_pin_cuts=full),status='GEOMETRY CANDIDATE; NOT A CONNECTED PLAN; NO ROUTE AUTHORIZED',die_outline_um=[W,H],
        unchanged_area=True,serdes_count=len(macros),serdes_power_w=round(14*4.37,2),slot_width_um=SLOT,
        changes=changed,rects=rects,overlaps=conflicts,outside=outside,macros=macros,packing=packing,
        affected_lane_center_lower_bounds=bounds,
        limitations=['Centre-distance hop counts are lower bounds, not priced added cycles. Actual face/core/FT stations must be re-solved.',
        'TX fresh current-default 626.4x544.32 placement/pin recut is owned S81-CORES; historical wrong-parameter view cannot be cropped.',
        'gunit input/output windows and parent relay routes need re-allocation despite unchanged internal core distances.',
        'Moving s_4N_x06 to SE and WS3 to north changes long logical paths: reject if registered routing cannot fit; report every actual added cycle to TOK.',
        'SerDes chains must be rerouted through interior neighbours; the215.88um core strip cannot retain all old E-W multi-link feedthrough chains.'])


def render(rep,out):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    fig,ax=plt.subplots(figsize=(13,11));W,H=rep['die_outline_um']
    for n,r in rep['rects'].items():
        color='#c7d1d9'
        if n in rep['changes']:color='#ffcf85'
        if n.startswith('lk_'):color='#b7d6ed'
        ax.add_patch(Rectangle((r[0],r[1]),r[2]-r[0],r[3]-r[1],facecolor=color,edgecolor='#555',linewidth=.3))
        if n in rep['changes']:ax.text((r[0]+r[2])/2,(r[1]+r[3])/2,n,ha='center',va='center',fontsize=5)
    for m in rep['macros']:
        r=m['macro_um'];ax.add_patch(Rectangle((r[0],r[1]),r[2]-r[0],r[3]-r[1],facecolor='#f99ac8',edgecolor='#912657',linewidth=.6))
    for n in ('gunit','bk_sel'):
        r=rep['rects'][n]
        for c in rep['packing'][n]['hard_cores']:
            x,y=c['origin_um'];w,h=c['outline_um'];ax.add_patch(Rectangle((r[0]+x,r[1]+y),w,h,facecolor='#6f9962',edgecolor='black',linewidth=.3))
    ax.set_xlim(0,W);ax.set_ylim(0,H);ax.set_aspect('equal');ax.set_xlabel('um');ax.set_ylabel('um')
    ax.set_title('S81 same-area PHY candidate: 9 north + 5 south, 14 x 3318x1013um macros\nGeometry only: TX rebuild and all changed registered routes/latency gates remain')
    fig.savefig(out,dpi=160,bbox_inches='tight')


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('plan',type=Path);ap.add_argument('--out',type=Path,required=True);args=ap.parse_args()
    rep=candidate(json.loads(args.plan.read_text()));args.out.mkdir(parents=True,exist_ok=True)
    (args.out/'candidate.json').write_text(json.dumps(rep,indent=2)+'\n');render(rep,args.out/'candidate.png')
    print(json.dumps({k:rep[k] for k in ('status','serdes_count','slot_width_um','overlaps','outside')},indent=2))
    print('packing',[(n,len(p['outside']),len(p['overlaps'])) for n,p in rep['packing'].items()])
    print('affected lanes',len(rep['affected_lane_center_lower_bounds']))


if __name__=='__main__':main()
