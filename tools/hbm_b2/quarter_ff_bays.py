#!/usr/bin/env python3
"""Joint row-site allocation for source-native quarter FFs; planning only, never route authority."""
import argparse, collections, json, math, re
from pathlib import Path

W, H, REACH = 1.08, .27, 405.


def load_problem(layout, output, control):
    nodes, edges, fixed, aliases = {}, [], {}, {}
    def node(name, point):
        point = tuple(map(float, point))
        if name in nodes and max(abs(a-b) for a,b in zip(nodes[name], point)) > .001:
            raise ValueError(f'conflicting source FF anchor {name}: {nodes[name]} vs {point}')
        nodes[name] = point
    def output_name(path, wp):
        m = re.fullmatch(r'gc(\d+)\.leaf\.(b_w|e_bus)', wp['identity'])
        if not m: raise ValueError(f'unknown native output identity {wp}')
        bit = path['c']*138 + (4+32*path['k']+path['bit'] if path['bit']<32 else path['k'])
        return f"ge[{path['e']}].gc[{m[1]}].leaf.{m[2]}[{bit}]"
    for p in output['paths']:
        names = []
        for wp in p['waypoints']:
            name = output_name(p, wp); node(name, wp['point_um']); names.append(name)
        src = f"@hcol:{p['e']}:{p['c']}:{p['k']}:{p['bit']}"
        dst = f"@tail:{p['e']}:{p['c']}:{p['k']}:{p['bit']}"
        fixed[src], fixed[dst] = tuple(p['source_um']), tuple(p['target_um'])
        edges += [(a,b,'output') for a,b in zip([src]+names, names+[dst]) if a!=b]
    for name, point in control['anchors'].items(): node(name, point)
    for a in control['arcs']:
        for key in ['source','target']:
            name, point = a[key], tuple(a[key+'_um'])
            if name not in nodes:
                if name in fixed and fixed[name] != point: raise ValueError('conflicting fixed endpoint '+name)
                fixed[name] = point
        edges.append((a['source'],a['target'],a['kind']))
    obstacles = []
    for kind in ['cores','tails','srams']:
        for obj in layout[kind]:
            x,y = obj['origin_um']; w,h = obj['outline_um']
            if kind=='tails': x,y = (1581.12, 950.4 if obj['name'].endswith('0') else 1209.6)
            obstacles.append(dict(name=obj['name'],kind=kind,rect=(x,y,x+w,y+h)))
    obstacles += [dict(name='clock:'+str(i),kind='clock',rect=tuple(x['island_um'])) for i,x in enumerate(layout['clock_sites'])]
    obstacles += [dict(name='bank:'+x['name'],kind='existing_bank',rect=tuple(x['rect_um'])) for x in layout['banks']]
    return nodes, fixed, sorted(set(edges)), obstacles


def distance(a,b): return abs(a[0]-b[0])+abs(a[1]-b[1])


def pack(nodes, fixed, edges, obstacles, max_radius=50., halo=0., directional=False):
    anchors = fixed | nodes
    budgets = {n:max_radius for n in nodes}; incident = collections.Counter()
    original_bad=[]
    for a,b,k in edges:
        d=distance(anchors[a],anchors[b]); slack=REACH-d
        if slack < -1e-6: original_bad.append(dict(source=a,target=b,kind=k,length_um=d))
        moving = int(a in nodes)+int(b in nodes)
        for n in (a,b):
            if n in nodes:
                budgets[n]=min(budgets[n], max(0.,slack/max(1,moving))); incident[n]+=1
    groups=collections.defaultdict(list)
    for n, xy in nodes.items():groups[xy].append(n)
    # Near-obstacle lists indexed by anchor avoid scanning all macros for every candidate slot.
    nearby={}
    for xy in groups:
        x,y=xy;r=max_radius+halo+W
        nearby[xy]=[o for o in obstacles if o['rect'][0]<x+r and o['rect'][2]>x-r and o['rect'][1]<y+r and o['rect'][3]>y-r]
    occupied, reserve = {}, {}
    placements, bays, failures = {}, [], []
    def candidates(xy, limit):
        x,y=xy; out=[]
        for iy in range(math.ceil((y-limit-H/2)/H),math.floor((y+limit-H/2)/H)+1):
            cy=(iy+.5)*H
            for ix in range(math.ceil((x-limit-W/2)/W),math.floor((x+limit-W/2)/W)+1):
                cx=(ix+.5)*W; d=abs(cx-x)+abs(cy-y)
                if d>limit+1e-7:continue
                rect=(cx-W/2,cy-H/2,cx+W/2,cy+H/2)
                if rect[0]<0 or rect[1]<0 or rect[2]>1816.992 or rect[3]>2347.488:continue
                hit=False
                for obs in nearby[xy]:
                    z=obs['rect'];h=halo if obs['kind'] in ('cores','tails','srams') else 0
                    if rect[0]<z[2]+h-1e-8 and rect[2]>z[0]-h+1e-8 and rect[1]<z[3]+h-1e-8 and rect[3]>z[1]-h+1e-8:
                        hit=True;break
                if not hit:out.append((d,ix,iy,cx,cy))
        return sorted(out)
    order=sorted(groups,key=lambda xy:(min(budgets[n] for n in groups[xy]),-len(groups[xy]),xy))
    for bay_id,xy in enumerate(order):
        names=sorted(groups[xy],key=lambda n:(budgets[n],-incident[n],n)); demand=len(names); extra=math.ceil(demand/.6)-demand
        # Tight FFs stay inside their proven per-edge movement budget; spare cells may extend to max_radius.
        pool=candidates(xy,max_radius); slots=[]; assigned=[]
        for name in names:
            bound=budgets[name]; chosen=None
            for c in pool:
                d,ix,iy,x,y=c
                if d>bound+1e-7:break
                if (ix,iy) not in occupied and (ix,iy) not in reserve:
                    chosen=c;break
            if chosen is None:
                failures.append(dict(bay=bay_id,anchor_um=xy,name=name,reason='NO_JOINT_SITE_WITHIN_REACH_BUDGET',movement_budget_um=round(bound,6),demand=demand))
                continue
            d,ix,iy,x,y=chosen;occupied[ix,iy]=name; placements[name]=(x,y); assigned.append(name);slots.append((ix,iy))
        blank=[]
        for d,ix,iy,x,y in pool:
            if len(blank)>=extra:break
            if (ix,iy) not in occupied and (ix,iy) not in reserve:
                reserve[ix,iy]=bay_id; blank.append((ix,iy));slots.append((ix,iy))
        if len(blank)!=extra:failures.append(dict(bay=bay_id,anchor_um=xy,reason='NO_JOINT_60PCT_SPARE_SITES',missing=extra-len(blank)))
        bays.append(dict(id=bay_id,anchor_um=xy,requested_ff=demand,placed_ff=len(assigned),spare_sites=len(blank),fill=len(assigned)/(len(assigned)+len(blank)) if assigned or blank else None,
                         max_displacement_um=max([distance(xy,placements[n]) for n in assigned]or[0]),sites=slots))
    initial_failures=list(failures)
    repaired=[]
    if directional:
        # The half-slack envelope is sufficient, not necessary. Once neighboring FFs have
        # actual sites, use their exact directional diamonds instead of declaring the
        # envelope failure physically impossible. Never move an already allocated FF.
        adjacent=collections.defaultdict(set)
        for a,b,_ in edges:
            adjacent[a].add(b); adjacent[b].add(a)
        owner={n:i for i,xy in enumerate(order) for n in groups[xy]}
        for name in sorted(set(nodes)-set(placements),key=lambda n:(len(adjacent[n]),n),reverse=True):
            i=owner[name]; xy=nodes[name]; actual=fixed | placements
            if any(n not in actual for n in adjacent[name]):continue
            for d,ix,iy,x,y in candidates(xy,max_radius):
                slot=(ix,iy)
                if slot in occupied or (slot in reserve and reserve[slot]!=i):continue
                if any(distance((x,y),actual[n])>REACH+1e-7 for n in adjacent[name]):continue
                reserve.pop(slot,None); occupied[slot]=name;placements[name]=(x,y);repaired.append(name);break
        failures=[f for f in failures if f.get('name') not in repaired and f['reason']!='NO_JOINT_60PCT_SPARE_SITES']
        for i,xy in enumerate(order):
            bay=bays[i];placed=[n for n in groups[xy] if n in placements]
            spare=[slot for slot,bid in reserve.items() if bid==i]
            need=math.ceil(len(placed)/.6)-len(placed)
            for d,ix,iy,x,y in candidates(xy,max_radius):
                if len(spare)>=need:break
                if (ix,iy) not in occupied and (ix,iy) not in reserve:
                    reserve[ix,iy]=i;spare.append((ix,iy))
            if len(spare)<need:failures.append(dict(bay=i,anchor_um=xy,reason='NO_JOINT_60PCT_SPARE_SITES',missing=need-len(spare)))
            bay.update(placed_ff=len(placed),spare_sites=len(spare),fill=len(placed)/(len(placed)+len(spare)) if placed or spare else None,
                       max_displacement_um=max([distance(xy,placements[n])for n in placed]or[0]),
                       sites=[slot for slot,n in occupied.items()if owner[n]==i]+spare)
    actual=fixed | placements; bad=[];missing=[];worst=(0,None)
    for a,b,k in edges:
        if a not in actual or b not in actual:missing.append((a,b,k));continue
        d=distance(actual[a],actual[b])
        if d>worst[0]:worst=(d,(a,b,k))
        if d>REACH+1e-6:bad.append(dict(source=a,target=b,kind=k,length_um=d))
    return dict(schema='opentallas.quarter_joint_ff_sites.v1',verdict='PASS_SUBSET_MODEL' if not(failures or original_bad or bad or missing) else 'FAIL',
                initial_envelope_failures=initial_failures,directionally_repaired=repaired,modeled_ff=len(nodes),placed_ff=len(placements),covered_edges=len(edges),missing_edges=len(missing),reach_failures=bad,original_reach_failures=original_bad,
                max_actual_hop_um=worst[0],worst_actual_edge=worst[1],bay_failures=failures,bays=bays,placements={n:list(p) for n,p in placements.items()},
                cell_um=[W,H],macro_halo_um=halo,max_search_radius_um=max_radius,
                qualification='Source-logical FF subset only; not mapped cell placement, G1, PG/clock/reset/hold closure or all native FFs. Exact disjoint row-cell sets reserve <=60% FF fill; all modeled paths checked at actual allocated centres. Other declared banks are obstacles. No RTL, cycles or plan edited.')


def render(layout, report, output):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import matplotlib.patches as patches
    fig,ax=plt.subplots(figsize=(11,13))
    _,_,_,obstacles=load_problem(layout,dict(paths=[]),dict(anchors={},arcs=[]))
    colors={'cores':'#e5e7eb','tails':'#f2b9ba','srams':'#bdd7ee','clock':'#d1b2ea','existing_bank':'#f6d795'}
    for o in obstacles:
        x,y,X,Y=o['rect'];ax.add_patch(patches.Rectangle((x,y),X-x,Y-y,facecolor=colors[o['kind']],edgecolor='#777',lw=.35))
    if report['placements']:
        points=list(report['placements'].values());ax.scatter([p[0]for p in points],[p[1]for p in points],s=.6,color='#137f54',label='Allocated source FF')
    fail=report['bay_failures'];xy={tuple(f['anchor_um'])for f in fail}
    if xy:ax.scatter([p[0]for p in xy],[p[1]for p in xy],s=35,marker='x',color='#c82525',label='Unplaced bank sites')
    ax.set(xlim=(0,1816.992),ylim=(0,2347.488),aspect='equal',xlabel='Quarter x (um)',ylabel='Quarter y (um)',title=f"Joint FF planning: {report['verdict']} | {report['placed_ff']}/{report['modeled_ff']} source FFs | {len(fail)} placement failures")
    ax.legend(loc='upper right');fig.tight_layout();fig.savefig(output,dpi=180);plt.close(fig)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('layout','outputs','controls','out'):p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--macro-halo',type=float,default=0.);p.add_argument('--max-radius',type=float,default=50.)
    p.add_argument('--directional-repair',action='store_true')
    p.add_argument('--cell-width',type=float,default=1.404,help='default reserves the wider native async FF; plain-data-only may use 1.08')
    a=p.parse_args()
    global W
    if a.cell_width < 1.08 or abs(a.cell_width/.054-round(a.cell_width/.054))>1e-7:
        p.error('cell width must be >=1.08 um on ASAP7 0.054-um sites')
    W=a.cell_width
    layout=json.loads(a.layout.read_text());nodes,fixed,edges,obstacles=load_problem(layout,json.loads(a.outputs.read_text()),json.loads(a.controls.read_text()))
    report=pack(nodes,fixed,edges,obstacles,a.max_radius,a.macro_halo,a.directional_repair);a.out.mkdir(parents=True,exist_ok=True)
    (a.out/'joint_ff_sites.json').write_text(json.dumps(report,indent=1)+'\n');render(layout,report,a.out/'joint_ff_sites.png')
    print(json.dumps({k:v for k,v in report.items()if k not in ('placements','bays','bay_failures','reach_failures','original_reach_failures','initial_envelope_failures','directionally_repaired')}))
    print('failure samples',report['bay_failures'][:5]);return 0 if report['verdict']=='PASS_SUBSET_MODEL' else 1

if __name__=='__main__':raise SystemExit(main())
