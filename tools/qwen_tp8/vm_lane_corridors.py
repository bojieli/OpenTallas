#!/usr/bin/env python3
"""Route source-pinned x-rotation lanes through registered free-space sites.
Experimental grid allocation, never physical closure. Wires cross real hard views only on their granted upper layers; registered sites remain outside every hard view. Fine cuts retain every
existing die bus, including the old VM bus footprint, as conservative demand.
"""
import argparse,heapq,json,math,sys,collections,tempfile
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'results/arch/qwen_tp8_1012'))
import cuts as C

def main():
    ap=argparse.ArgumentParser();ap.add_argument('net');ap.add_argument('plan');ap.add_argument('out');ap.add_argument('--disperse',action='store_true');ap.add_argument('--drop-obsolete-vm',action='store_true');ap.add_argument('--transpose-bank',action='store_true');a=ap.parse_args()
    d=json.loads(Path(a.net).read_text());p=json.loads(Path(a.plan).read_text())
    children=p['flattened_child_alternative']['children'];g={v['region']:v for v in children}
    # Recover region origins from exact first bank child coordinates, not rounded geometry.
    origins={k:(next(v for v in children if v['region']==k and v['n'].endswith('bank_t_0'))['x']-43.2,
                next(v for v in children if v['region']==k and v['n'].endswith('bank_t_0'))['y']-86.4) for k in range(8)}
    old=[i for i in d['insts'] if i['n']!='sp_vector_memory' and not i['m'].startswith(('qfd_rly','qkd_rly'))]
    obstacles=old+children
    C.CAP_MODE='v3';C.CLUSTER=C.CLUSTER+('ot_qfd_vm_grp',)
    blocks,cap5,clb=C.block_model(obstacles)
    removed=[]
    if a.drop_obsolete_vm:
        removed=[b[0] for b in d['buses'] if 'sp_vector_memory' in b[3] and b[1]!='clock_trunk']
        baseline=dict(d,buses=[b for b in d['buses'] if b[0] not in removed])
        with tempfile.NamedTemporaryFile(mode='w',suffix='.json') as tmp:
            json.dump(baseline,tmp);tmp.flush();base=C.Net(tmp.name)
    else:base=C.Net(a.net)
    tile=[i for i in old if i['m']=='qfd_tile_nk'];col=sorted(set(i['x'] for i in tile));tw=tile[0]['w']
    channels=[(x+tw,z) for x,z in zip(col,col[1:]) if 40<z-x-tw<200]
    X={round((lo+hi)/2,6) for lo,hi in channels}
    X.update(round(i['x']+i['w']+10.8,6) for i in obstacles if 13288<i['x']<18467)
    X.update(round(i['x']-10.8,6) for i in obstacles if 13288<i['x']<18467)
    Y=set(float(v) for v in np.arange(8350,17400,432))
    anchor={}
    for k,(x,y) in origins.items():
        for bank in range(8):
            for stage in range(-1,6):
                relative_y=([1025.28,64.8,278.64,494.64,1080.,764.64,1025.28][stage+1]
                            if a.disperse else 1036.8+stage*15.12)
                point=(round(x+64.8+bank*129.6,6),round(y+relative_y,6))
                anchor[k,bank,stage]=point;X.add(point[0]);Y.add(point[1])
    # Additional legal relay rows above/below hard views. Site legality remains a
    # point/clearance check; final synthesized clusters need sized placement.
    for i in obstacles:
        if i['x']<18467 and i['x']+i['w']>13288:
            Y.update((round(i['y']-10.8,6),round(i['y']+i['h']+10.8,6)))
    X=sorted(x for x in X if 4000<x<28000);Y=sorted(y for y in Y if 8350<y<17400)
    xi={x:i for i,x in enumerate(X)};yi={y:i for i,y in enumerate(Y)}
    B=np.array([(i['x']-2.16,i['y']-2.16,i['x']+i['w']+2.16,i['y']+i['h']+2.16) for i in obstacles])
    legal={}
    for ix,x in enumerate(X):
        for iy,y in enumerate(Y):
            legal[ix,iy]=not np.any((B[:,0]<x)&(x<B[:,2])&(B[:,1]<y)&(y<B[:,3]))
    assert all(legal[xi[x],yi[y]] for x,y in anchor.values()),'regional root point collision'
    cap_cache={};used=collections.defaultdict(int)
    def edge(u,v):
        ux,uy=u;vx,vy=v
        ax='x' if uy==vy else 'y'
        lowindex=min(ux,vx) if ax=='x' else min(uy,vy)
        highindex=max(ux,vx) if ax=='x' else max(uy,vy)
        coordinate=X if ax=='x' else Y
        other=Y[uy] if ax=='x' else X[ux]
        start=math.floor(other/130)*130
        keys=[]
        for index in range(lowindex,highindex):
            for window in (start-130,start):
                key=(ax,index,window);keys.append(key)
                if key not in cap_cache:
                    bounds=np.array([window,window+260.])
                    lo,hi=coordinate[index:index+2]
                    samples=[(lo+hi)/2]+list(np.arange(math.ceil(lo/50)*50,hi,50))
                    reserve=float('inf')
                    for cp in samples:
                        capacity,_=C.usable(ax,cp,bounds,blocks,cap5,clb)
                        bits=base.cut(ax,cp,bounds)[0][0]
                        reserve=min(reserve,.60*capacity[0]-bits)
                    cap_cache[key]=max(0.,reserve)
        remaining=min(cap_cache[k]-used[k] for k in keys)
        if ax=='y':
            for lo,hi in channels:
                if lo<other<hi:
                    remaining=min(remaining,.60*(hi-lo)*(.75/.08+.75/.064+.5/.048)-max(used[k] for k in keys))
                    break
        length=abs(X[ux]-X[vx])+abs(Y[uy]-Y[vy])
        return keys,remaining,length
    def route(start,goal,avoid):
        if start==goal:return [start]
        h=lambda n:(abs(X[n[0]]-X[goal[0]])+abs(Y[n[1]]-Y[goal[1]]))/432
        heap=[(h(start),0.,start)];dist={start:0.};prev={};closed=set()
        while heap:
            _,cost,u=heapq.heappop(heap)
            if u in closed:continue
            if u==goal:
                path=[u]
                while u in prev:u=prev[u];path.append(u)
                return path[::-1]
            closed.add(u)
            ix,iy=u
            for dx,dy in ((-1,0),(1,0),(0,-1),(0,1)):
                v=(ix+dx,iy+dy)
                # Wires may cross a hard M5/M7 view on its granted upper die
                # layers; only register endpoints need free placement sites.
                while v in legal and not legal[v]:
                    length=abs(X[v[0]]-X[ix])+abs(Y[v[1]]-Y[iy])
                    if length>500:break
                    v=(v[0]+dx,v[1]+dy)
                if not legal.get(v,False) or v in closed:continue
                keys,rem,length=edge(u,v)
                if rem<256 or length>500 or any(k in avoid for k in keys):continue
                step=length/432+0.05+256/(rem+1)
                alt=cost+step
                if alt<dist.get(v,float('inf')):
                    dist[v]=alt;prev[v]=u;heapq.heappush(heap,(alt+h(v),alt,v))
        return None
    locate=lambda b,s:anchor[b%8,b//8,s] if a.transpose_bank else anchor[b//8,b%8,s]
    jobs=[]
    for s,shift in enumerate((8,16,32,1,2,4)):
        for b in range(64):
            for kind,source in (('alternate',(b+shift)%64),('bypass',b)):
                A=locate(source,s-1);Q=locate(b,s)
                for lane in range(2):
                    jobs.append(dict(name=f's{s}_b{b}_{kind}_l{lane}',stage=s,kind=kind,source_bank=source,sink_bank=b,
                                     lane=lane,bits=256,A=A,Q=Q,lower_um=abs(A[0]-Q[0])+abs(A[1]-Q[1])))
    jobs.sort(key=lambda v:-v['lower_um']);paths=[];fail=[]
    for num,j in enumerate(jobs):
        st=(xi[j['A'][0]],yi[j['A'][1]]);go=(xi[j['Q'][0]],yi[j['Q'][1]])
        avoid=set()
        while True:
            path=route(st,go,avoid)
            if path is None:break
            demand=collections.Counter()
            for u,v in zip(path,path[1:]):
                keys,_,_=edge(u,v)
                demand.update({key:256 for key in keys})
            bad={key for key,n in demand.items() if used[key]+n>cap_cache[key]}
            if not bad:break
            # A detour can cross the SAME fine window repeatedly. Include its
            # self-demand before acceptance rather than overbooking the window.
            avoid.update(bad)
        if path is None:fail.append(j);continue
        for u,v in zip(path,path[1:]):
            keys,_,_=edge(u,v)
            for key in keys:used[key]+=256
        # Preserve legal bends and choose the farthest legal grid point within
        # 500um on each straight run. Tiny grid intervals are not new stages.
        compact=[path[0]];at=0
        while at<len(path)-1:
            end=at+1;direction=(path[end][0]-path[at][0],path[end][1]-path[at][1])
            while end+1<len(path):
                delta=(path[end+1][0]-path[end][0],path[end+1][1]-path[end][1])
                same=(direction[0]==0 and delta[0]==0) or (direction[1]==0 and delta[1]==0)
                length=abs(X[path[end+1][0]]-X[path[at][0]])+abs(Y[path[end+1][1]]-Y[path[at][1]])
                if not same or length>500:break
                end+=1
            compact.append(path[end]);at=end
        points=[[X[ix],Y[iy]] for ix,iy in compact]
        paths.append(dict(j,points=points,registered_wire_stages=len(points)-1,
                          route_um=sum(abs(a[0]-b[0])+abs(a[1]-b[1]) for a,b in zip(points,points[1:]))))
        if num%128==0:print(f'{num}/{len(jobs)} routed={len(paths)} failed={len(fail)}',flush=True)
    segments=[]
    for link in paths:
        for A,Q in zip(link['points'],link['points'][1:]):segments.append(A+Q+[256])
    if segments:
        S=np.array(segments);worst=[]
        for ax,axis,other,span in [('x',0,1,np.arange(4000,28000,100)),('y',1,0,np.arange(8350,17400,100))]:
            edges=np.arange(8320,17600,130.) if ax=='x' else np.arange(3900,28200,130.)
            for cp in span:
                m=(np.minimum(S[:,axis],S[:,axis+2])<cp)&(cp<np.maximum(S[:,axis],S[:,axis+2]))
                T=S[m];o=T[:,other]+(T[:,other+2]-T[:,other])*(cp-T[:,axis])/(T[:,axis+2]-T[:,axis])
                for low in edges[:-2]:
                    bits=int(T[(o>=low)&(o<low+260),4].sum())
                    if not bits:continue
                    bounds=np.array([low,low+260]);capacity,_=C.usable(ax,cp,bounds,blocks,cap5,clb)
                    oldbits=int(base.cut(ax,cp,bounds)[0][0]);util=(oldbits+bits)/capacity[0]
                    worst.append(dict(ax=ax,pos=float(cp),win=[float(low),float(low+260)],new_bits=bits,
                                      existing_bits=oldbits,usable=float(capacity[0]),util=float(util)))
        worst.sort(key=lambda x:-x['util'])
    else:worst=[]
    depths={s:max((v['registered_wire_stages'] for v in paths if v['stage']==s),default=0) for s in range(6)}
    report=dict(status='ROUTING_CANDIDATE_ONLY',scope='x six-stage rotation alternatives AND bypasses, full64x512 shape. Excludes bank FIFO, descriptors/writes, SU/row/final fanout, clock/PDN.',
        transpose_bank=a.transpose_bank,logical_bank_map=({'region': 'bank mod8','localbank':'bank div8'} if a.transpose_bank else {'region':'bank div8','localbank':'bank mod8'}),dispersed_stage_rows=a.disperse,grid=dict(x_um=X,y_um=Y,legal_point_count=sum(legal.values()),max_seam_um=500,
                  note='Relay POINTS have2.16um clearance; cell cluster area, sites, clocks and PDN unverified.'),
        obsolete_vm_endpoint_nets_removed=removed,accounting='Every retained existing die bus used as baseline; no duty-factor discount. Two overlapping260um windows per edge. Independent final100um cut scan.',
        lanes_requested=len(jobs),lanes_routed=len(paths),lanes_failed=len(fail),failed=fail,paths=paths,
        stage_equalized_wire_depths=depths,stage_latency_including_mux={s:n+1 for s,n in depths.items()},
        relay_slice_bits=128,
        local_root_max_flops=max((128+7)*(n+1) for n in depths.values()),fine_worst=worst[:20],
        verdict='REJECT' if fail or (worst and worst[0]['util']>.60) else 'PASS_TRANSPORT_GRID_ONLY',
        required=['All lanes must route; final fine target <=.60','Synthesize and size every register cluster; eachroot <=15ksinks','Match paths, bypasses and tags to declared stage depth','Implement and check otherVM interfaces, finitecredits and write/read old-word ordering'])
    Path(a.out).write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ('verdict','lanes_requested','lanes_routed','lanes_failed','stage_equalized_wire_depths','local_root_max_flops')}),flush=True)
    print(json.dumps(worst[0] if worst else {}),flush=True)
if __name__=='__main__':main()
