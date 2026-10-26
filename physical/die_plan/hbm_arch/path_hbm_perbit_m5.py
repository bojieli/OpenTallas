#!/usr/bin/env python3
"""Siting for M5 hard-core plans: wires may use M6/M7; relay CELLS avoid core halos.

Each bit follows its own legal station targets. Unlike a centroid cluster this
preserves wide face ribbons. This is a placement proposal, never a route receipt.
"""
import argparse, collections, copy, json, math, shutil, sys
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent; ROOT=HERE.parents[2]
sys.path[:0]=[str(ROOT),str(ROOT/'tools/die_plan')]
import schema as S
from gen_phys import type_pins
from tools.die_trial.legal_sites import RowAllocator

REACH=323.0  # reserve 2*40um cell displacement plus data-pin offsets below405
RADIUS=80.0
CELL=np.array([1.404,.27])
_NEIGHBORS={}
AGGRESSIVE=False

def neighbors(targets,node):
    if node not in _NEIGHBORS:
        _NEIGHBORS[node]=np.flatnonzero(np.abs(targets-targets[node]).sum(axis=1)<=REACH).astype(np.int32)
    return _NEIGHBORS[node]



def path_for(a,b,targets):
    """Shortest target chain, exact BFS with a direct-goal shortcut."""
    if np.abs(a-b).sum()<=REACH:return []
    first=np.abs(targets-a).sum(axis=1);last=np.abs(targets-b).sum(axis=1)
    starts=np.flatnonzero(first<=REACH)
    if not len(starts):raise ValueError('no legal cell corridor within reach of input bit')
    common=starts[last[starts]<=REACH]
    if len(common):return [int(common[np.argmin(first[common]+last[common]+.001*np.abs(targets[common]-(a+b)/2).sum(axis=1))])]
    # Greedy toward capture is normally enough when wires may cross M5 cores.
    desired=a+(b-a)*min(.75*REACH/float(np.abs(b-a).sum()),1.0)
    node=int(starts[np.argmin(last[starts] if AGGRESSIVE else np.abs(targets[starts]-desired).sum(axis=1))]);path=[node];seen={node}
    while True:
        ids=neighbors(targets,node)
        ids=ids[last[ids]<last[node]-1e-6]
        if not len(ids):break
        desired=targets[node]+(b-targets[node])*min(.75*REACH/float(last[node]),1.0)
        node=int(ids[np.argmin(last[ids] if AGGRESSIVE else np.abs(targets[ids]-desired).sum(axis=1))]);path.append(node)
        if last[node]<=REACH:return path
        if node in seen:break
        seen.add(node)
    parent=np.full(len(targets),-2,dtype=int);parent[starts]=-1
    queue=collections.deque(map(int,starts));end=None
    while queue:
        node=queue.popleft()
        if last[node]<=REACH:end=node;break
        ids=neighbors(targets,node)
        ids=ids[parent[ids]==-2]
        ids=ids[np.argsort(last[ids])];parent[ids]=node;queue.extend(map(int,ids))
    if end is None:raise ValueError('no reach-bounded per-bit cell corridor')
    out=[]
    while end>=0:out.append(int(end));end=parent[end]
    return out[::-1]


def repair_type(raw,tn):
    _NEIGHBORS.clear()
    t=raw['partition_types'][tn];w,h=t['outline_um']
    cores=t.get('hard_cores',[])
    for c in cores:
        x,y=c['origin_um'];cw,ch=c['outline_um']
        if min(x,y)<-1e-6 or x+cw>w+1e-6 or y+ch>h+1e-6:
            raise ValueError(f'{tn}/{c["inst"]}: core outside unchanged outline')
        for d in cores:
            if d is c:continue
            u,v=d['origin_um'];dw,dh=d['outline_um']
            if min(x+cw,u+dw)>max(x,u)+1e-6 and min(y+ch,v+dh)>max(y,v)+1e-6:
                raise ValueError(f'{tn}: overlap {c["inst"]}/{d["inst"]}')
        if int(c.get('obs_max','M7')[1:])>5:raise ValueError(tn+': wire-over-core requires M5 ceiling')
    boxes=list(S.placed_macro_boxes(t,halo=8.64).values())
    # Full footprints must clear the halo, not merely cell centres.
    alloc=RowAllocator((4.32,4.32,w-4.32,h-4.32),blocked=boxes,cell_size=CELL,
                       column_pitch=2.16,row_pitch=.27,origin=(4.32,4.32))
    # Include legal cell columns beside each halo; a coarse8.64um grid
    # misses physically usable strips narrower than one grid step.
    cols=set(range(alloc.ix0,alloc.ix1+1,4))
    for a,b,c,d in boxes:
        for bound in (a-CELL[0]/2,c+CELL[0]/2):
            k=round((bound-alloc.ox-CELL[0]/2)/alloc.cp)
            cols.update(range(max(alloc.ix0,k-2),min(alloc.ix1,k+2)+1))
    xs=np.array([alloc.ox+k*alloc.cp+CELL[0]/2 for k in sorted(cols)])
    rows=set(range(alloc.iy0,alloc.iy1+1,32))
    for a,b,c,d in boxes:
        for bound in (b-CELL[1]/2,d+CELL[1]/2):
            k=round((bound-alloc.oy-CELL[1]/2)/alloc.rp)
            rows.update(range(max(alloc.iy0,k-2),min(alloc.iy1,k+2)+1))
    ys=np.array([alloc.oy+k*alloc.rp+CELL[1]/2 for k in sorted(rows)])
    x,y=np.meshgrid(xs,ys);targets=np.column_stack((x.ravel(),y.ravel()))
    ok=np.ones(len(targets),bool)
    for a,b,c,d in boxes:
        ok &= ~((targets[:,0]-CELL[0]/2<c)&(targets[:,0]+CELL[0]/2>a)&
                (targets[:,1]-CELL[1]/2<d)&(targets[:,1]+CELL[1]/2>b))
    targets=targets[ok]
    if not len(targets):raise ValueError(tn+': no cell targets clear the halos')
    model=S.Plan(raw);pins={(b,i):np.array([x,y]) for b,i,_,x,y,_ in type_pins(model,tn)}
    report=[]
    for slot in sorted(t.get('ft_slots',[]),key=lambda s:-s['width']):
        name=slot['name'];n=slot['width']+1;old=slot['stations']
        print(tn,name,'START',n,'bits',old,'stations',flush=True)
        a=np.array([pins[name+'_i',i] for i in range(n)]);b=np.array([pins[name+'_o',i] for i in range(n)])
        paths=[]
        for bit,(p,q) in enumerate(zip(a,b)):
            try:paths.append(path_for(p,q,targets))
            except ValueError as error:raise ValueError(f'{tn}/{name}[{bit}] {p.tolist()}->{q.tolist()}: {error}') from error
        count=max(old-1,max(map(len,paths),default=0))
        if count==0:
            for key in ('regs_um','bit_sites_um','bit_site_cell_um'):slot.pop(key,None)
            report.append(dict(slot=name,bits=n,before=old,after=1,max_hop_um=float(np.abs(b-a).sum(axis=1).max())))
            continue
        # Preserve static depth: distinct physical cells may share one legal
        # target neighbourhood. Added stages get real cells, never aliases.
        for k,path in enumerate(paths):
            if not path:
                ids=np.flatnonzero((np.abs(targets-a[k]).sum(axis=1)<=REACH)&(np.abs(targets-b[k]).sum(axis=1)<=REACH))
                if not len(ids):raise ValueError(tn+'/'+name+': no site to preserve existing pipeline depth')
                path.append(int(ids[np.argmin(np.abs(targets[ids]-(a[k]+b[k])/2).sum(axis=1))]))
            while len(path)<count:
                chain=[a[k],*[targets[i] for i in path],b[k]]
                edge=max(range(len(chain)-1),key=lambda j:float(np.abs(chain[j+1]-chain[j]).sum()))
                left,right=chain[edge],chain[edge+1]
                ids=np.flatnonzero((np.abs(targets-left).sum(axis=1)<=REACH)&(np.abs(targets-right).sum(axis=1)<=REACH))
                if not len(ids):raise ValueError(tn+'/'+name+': cannot preserve static depth at legal cell sites')
                target=int(ids[np.argmin(np.abs(targets[ids]-(left+right)/2).sum(axis=1))])
                path.insert(edge,target)
        sites=np.empty((count,n,2))
        for bit,path in enumerate(paths):
            for stage,index in enumerate(path):
                rejected=[]
                prev=a[bit] if stage==0 else sites[stage-1,bit]
                following=b[bit] if stage+1==count else targets[path[stage+1]]
                try:
                    for attempt in range(512):
                        pts,_=alloc.allocate(targets[index],1,max_radius_um=RADIUS)
                        point=pts[0]
                        if np.abs(point-prev).sum()<=403+1e-6 and np.abs(point-following).sum()<=403+1e-6:
                            sites[stage,bit]=point;break
                        ix=round((point[0]-alloc.cw/2-alloc.ox)/alloc.cp)
                        iy=round((point[1]-alloc.ch/2-alloc.oy)/alloc.rp)
                        rejected.append((iy-alloc.iy0)*alloc.nx+ix-alloc.ix0)
                    else:raise ValueError('no candidate preserves both paired-bit legs')
                except ValueError as error:
                    raise ValueError(f'{tn}/{name}[{bit}] stage{stage+1} target{targets[index].tolist()}: {error}') from error
                finally:alloc.used.difference_update(rejected)
        chain=[a,*sites,b];worst=max(float(np.abs(q-p).sum(axis=1).max()) for p,q in zip(chain,chain[1:]))
        if worst>403+1e-6:raise ValueError(f'{tn}/{name}: paired-bit hop{worst}>403')
        slot['stations']=count+1;slot['regs_um']=[a.mean(axis=0).round(4).tolist(),*sites.mean(axis=1).round(4).tolist()]
        slot['bit_site_cell_um']=CELL.tolist();slot['bit_sites_um']=(sites-CELL/2).round(6).tolist()
        report.append(dict(slot=name,bits=n,before=old,after=count+1,max_hop_um=round(worst,4)))
        print(tn,name,'PASS',report[-1],flush=True)
    return report


def main():
    global REACH,AGGRESSIVE
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--src',required=True,type=Path);ap.add_argument('--out',required=True,type=Path);ap.add_argument('--types',required=True);ap.add_argument('--bank-corridors',action='store_true');ap.add_argument('--placements',type=Path);ap.add_argument('--short-targets',action='store_true');ap.add_argument('--su-corridors',action='store_true');ap.add_argument('--reach-budget',type=float,default=323.0);a=ap.parse_args()
    if not 0<a.reach_budget<=403:raise SystemExit('reach budget must be in(0,403]')
    REACH=a.reach_budget
    AGGRESSIVE=a.short_targets
    if a.out.exists():raise SystemExit('output must be new')
    raw=json.loads((a.src/'die_plan.json').read_text());before=S.Plan(copy.deepcopy(raw));rep={}
    if a.bank_corridors:
        # Open W and two internal strips, without changing the outline or cores.
        # Origins preserve M4/M5 track phases (0.192um common lattice).
        # Narrow strips include actual row-legal FF columns, not grid centroids.
        t=raw['partition_types']['q_b100']
        for c in (t['hard_cores'] if 'q_b100' in a.types.split(',') else []):
            col=round((c['origin_um'][0]-8.64)/233.28)
            c['origin_um'][0]=[14.592,256.512,498.432][col]
            c['origin_um'][1]=round(c['origin_um'][1]+17.28,6)
        if 'q_b110' in a.types.split(','):
            cores=sorted(raw['partition_types']['q_b110']['hard_cores'],key=lambda c:c['origin_um'][1])
            for c,y in zip(cores,[60.48,432.0,803.52,1175.04]):c['origin_um'][1]=y
    if a.su_corridors:
        for tn in a.types.split(','):
            if tn in ('q_su21','q_su31'):
                for c in raw['partition_types'][tn]['hard_cores']:
                    x,y=c['origin_um']
                    if tn=='q_su21':c['origin_um'][0]=25.92 if x<400 else 864.0
                    else:c['origin_um'][0]=x+(86.4 if x>400 else 0)
                    c['origin_um'][1]=34.56 if y<400 else (786.24 if tn=='q_su31' else 803.52)
            elif tn=='q_su30':
                for c in raw['partition_types'][tn]['hard_cores']:
                    if c['outline_um'][0]<700:continue
                    x,y=c['origin_um'];c['origin_um'][0]=x+(17.28 if x in(803.52,1270.08) else 0)-(69.12 if y>400 else 0)
                    c['origin_um'][1]=8.64 if y<400 else 777.6
    if a.placements:
        placement=json.loads(a.placements.read_text());tn=placement['type']
        if tn not in a.types.split(','):raise ValueError('placement type not selected')
        cores=raw['partition_types'][tn]['hard_cores'];mapped=placement['placements']
        if {c['inst'] for c in cores}!=set(mapped):raise ValueError('placement instance mismatch')
        for c in cores:c['origin_um']=mapped[c['inst']]
    shutil.copytree(a.src,a.out)
    try:
        for tn in a.types.split(','):rep[tn]=repair_type(raw,tn)
    except Exception as error:
        (a.out/'failed_partial_plan.json').write_text(json.dumps(raw,indent=1)+'\n')
        (a.out/'perbit_m5_failure.json').write_text(json.dumps(dict(verdict='FAIL',reason=str(error),completed_types=rep,not_release_ready=True),indent=1)+'\n')
        raise
    model=S.Plan(raw);raw['latency']['lanes']={lid:model.lane_latency(lid) for lid in model.lanes}
    delta={lid:model.lane_latency(lid)['cycles']-before.lane_latency(lid)['cycles'] for lid in model.lanes if model.lane_latency(lid)['cycles']!=before.lane_latency(lid)['cycles']}
    (a.out/'die_plan.json').write_text(json.dumps(raw,indent=1)+'\n');(a.out/'perbit_m5_report.json').write_text(json.dumps(dict(types=rep,lane_cycle_delta=delta,scope='geometry proposal; internal station/reset/clock rebuild and review required'),indent=1)+'\n')
    print('COMPLETE',json.dumps(delta),flush=True)
if __name__=='__main__':main()
