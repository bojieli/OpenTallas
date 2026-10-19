#!/usr/bin/env python3
"""Additive native-pin reset routing candidate; never clock/phase admission.

Existing loads/edges are immutable. Only spare fanout on an exactly traced
same-root/same-clock existing output can seed a new branch. New release depths
are reported rather than disguised as inherited-depth-preserving branches.
"""
import argparse, collections, hashlib, heapq, json, math, re
from pathlib import Path
import kv_fault_plane as I

CELL=12.96
REACH=405.0
AIN=(.042,6.492)
BOUT=(12.918,6.492)
def dist(a,b):return abs(a[0]-b[0])+abs(a[1]-b[1])
def norm(s):return re.sub(r'\[0\]$','',s or '')

class Space:
    def __init__(self,rects):
        self.bins=collections.defaultdict(list)
        self.limit=[max(r[2] for r in rects),max(r[3] for r in rects)]
        for r in rects:self.add(r)
    def keys(self,r):
        for x in range(math.floor(r[0]/100),math.floor(r[2]/100)+1):
            for y in range(math.floor(r[1]/100),math.floor(r[3]/100)+1):yield x,y
    def add(self,r):
        for k in self.keys(r):self.bins[k].append(r)
    def free(self,g):
        x,y=[v*CELL for v in g]
        if min(x,y)<0 or x+CELL>self.limit[0] or y+CELL>self.limit[1]:return False
        r=[x-.5,y-.5,x+CELL+.5,y+CELL+.5]
        return not any(r[0]<q[2] and q[0]<r[2] and r[1]<q[3] and q[1]<r[3] for k in self.keys(r) for q in self.bins[k])

def plan(run,inv,candidate,manifest,skew):
    if skew<0:raise ValueError('Root assertion skew budget must be nonnegative')
    P=I.P;nets,_,_,insts=P.parse_die(str(run/'case_kv/die.v'))
    # Counting every occurrence is conservative, including unfamiliar ports.
    uses=collections.Counter()
    for _,_,_,ports in insts:
        for expr in ports.values():
            bits=P.expr_bits(expr,nets)
            if bits is None and expr.strip():raise ValueError('Unresolved expression prevents conservative reset fanout counting: '+expr)
            uses.update(b for b in (bits or []) if b[0]!='CONST')
    rects=list(inv['physical_obstacles'])
    for n in candidate['nodes']:
        x,y=n['placement']['x'],n['placement']['y'];rects.append([x,y,x+21.6,y+21.6])
    space=Space(rects);groups=collections.defaultdict(list);stations=[];targets=[]
    for n in manifest['existing_reset_nodes']:
        remaining=32-max(0,uses[tuple(n['output_bit'])]-1)
        if remaining<=0:continue
        groups[(n['root_id'],norm(n['clock']))].append(dict(id=n['instance'],xy=n['output_pin_xy'],depth=n['depth_from_root'],remaining=remaining,output_bit=n['output_bit'],existing=True))
    def pin(g,offset):return [g[k]*CELL+offset[k] for k in (0,1)]
    moves=[(d,0) for d in (-24,-16,-8,-4,-2,2,4,8,16,24)]+[(0,d) for d in (-24,-16,-8,-4,-2,2,4,8,16,24)]+[(x,y) for x in (-12,-6,6,12) for y in (-12,-6,6,12)]
    def route(seed,target):
        if dist(seed['xy'],target)<=REACH:return []
        g0=tuple(round(v/CELL) for v in seed['xy']);heap=[];cost={};parent={}
        for dx in range(-5,6):
            for dy in range(-5,6):
                g=(g0[0]+dx,g0[1]+dy)
                if space.free(g) and dist(seed['xy'],pin(g,AIN))<=REACH:
                    c=dist(seed['xy'],pin(g,AIN));cost[g]=c;parent[g]=None;heapq.heappush(heap,(c+dist(pin(g,BOUT),target),g))
        seen=set();goal=None
        while heap and len(seen)<100000:
            _,g=heapq.heappop(heap)
            if g in seen:continue
            seen.add(g);p=pin(g,BOUT)
            if dist(p,target)<=REACH:goal=g;break
            for dx,dy in moves:
                h=(g[0]+dx,g[1]+dy)
                d=dist(p,pin(h,AIN))
                if d>REACH or not space.free(h):continue
                c=cost[g]+d+20
                if c<cost.get(h,float('inf')):
                    cost[h]=c;parent[h]=g;heapq.heappush(heap,(c+dist(pin(h,BOUT),target),h))
        if goal is None:raise ValueError('No legal reset corridor from '+seed['id']+' to '+str(target))
        path=[]
        while goal is not None:path.append(goal);goal=parent[goal]
        return list(reversed(path))
    def append(seed,g,key):
        x,y=[v*CELL for v in g];p=pin(g,AIN)
        if seed['remaining']<=0 or dist(seed['xy'],p)>REACH+1e-6 or not space.free(g):raise ValueError('Invalid additive branch '+str(dict(seed=seed,g=g,distance=dist(seed['xy'],p),free=space.free(g))))
        seed['remaining']-=1;name='fault_reset_branch_'+str(len(stations))
        n=dict(id=name,master='qkd_rlys_1',source=seed['id'],root_id=key[0],clock=key[1],depth=seed['depth']+1,placement=dict(x=x,y=y,orient='R0'),input_xy=p,output_xy=pin(g,BOUT),edge_um=dist(seed['xy'],p))
        stations.append(n);space.add([x,y,x+CELL,y+CELL]);new=dict(id=name,xy=n['output_xy'],depth=n['depth'],remaining=32,existing=False)
        groups[key].append(new);return new
    for load in manifest['loads']:
        key=(load['root_details']['id'],norm(load['clock']));available=[n for n in groups[key] if n['remaining']>0]
        if not available:raise ValueError('No same-clock/root spare seed '+str(key))
        seed=min(available,key=lambda n:(dist(n['xy'],load['native_pin_xy']),n['depth'],n['id']))
        for g in route(seed,load['native_pin_xy']):seed=append(seed,g,key)
        seed['remaining']-=1
        targets.append(dict(instance=load['instance'],node=load['instance'][3:],source=seed['id'],root_id=key[0],clock=key[1],depth=seed['depth'],inherited_depth=load['required_target_depth'],depth_delta=seed['depth']-load['required_target_depth'],pin_xy=load['native_pin_xy'],edge_um=dist(seed['xy'],load['native_pin_xy'])))
    # Full graph downstream distances, excluding each node's own capture edge.
    ops={n['id']:n for n in candidate['nodes']};ops.update({n['id']:n for n in candidate['transports']})
    downstream={candidate['sink']:0}
    while True:
        changed=False
        for name,n in ops.items():
            if name not in downstream:continue
            refs=[n['source']] if 'source' in n else [n['a'],n['b']]
            for ref in set(refs)-{name}:
                age=downstream[name]+n.get('latency_cycles',1)
                if age>downstream.get(ref,-1):downstream[ref]=age;changed=True
        if not changed:break
    # Source reset depth is measured on the exact original reset graph.
    reset_edges={}
    reset_instances={n['instance'] for n in manifest['existing_reset_nodes']}
    for master,i,_,ports in insts:
        if master=='qkd_rlys_1' and i in reset_instances:
            a=P.expr_bits(ports['a'],nets);b=P.expr_bits(ports['b'],nets)
            if len(a or [])==len(b or [])==1:reset_edges[b[0]]=a[0]
    source_clears=[]
    for s in candidate['sources']:
        bit=P.expr_bits(s['reset'],nets)
        if len(bit or [])!=1:raise ValueError('Unresolved source reset')
        b=bit[0];depth=0;seen=set()
        while b in reset_edges:
            if b in seen:raise ValueError('Reset cycle')
            seen.add(b);b=reset_edges[b];depth+=1
        source_clears.append(dict(id=s['id'],clock=s['clock'],root_bit=list(b),depth=depth,downstream=downstream[s['id']]))
    sink=candidate['sink'];sinkrow=next(t for t in targets if t['node']==sink)
    # A diagnostic skew budget is explicit. Production cannot accept it without
    # native root/clock phase receipts. Delaying assertion is intentional: the
    # final sticky clear occurs after all stale sources and pipelines flush.
    bound=max([t['depth']+downstream[t['node']] for t in targets if t['node']!=sink]+[s['depth']+s['downstream'] for s in source_clears])+skew+2
    key=(sinkrow['root_id'],sinkrow['clock']);seed=next(n for n in groups[key] if n['id']==sinkrow['source']);seed['remaining']+=1
    while seed['depth']<bound:
        g0=[round(v/CELL) for v in seed['xy']];choices=[]
        for dx in range(-15,16):
            for dy in range(-15,16):
                g=(g0[0]+dx,g0[1]+dy)
                if space.free(g) and dist(seed['xy'],pin(g,AIN))<=REACH and dist(pin(g,BOUT),sinkrow['pin_xy'])<=REACH:
                    choices.append((dist(pin(g,BOUT),sinkrow['pin_xy']),g))
        if not choices:raise ValueError('No legal delay site near sticky sink')
        seed=append(seed,min(choices)[1],key)
    seed['remaining']-=1;sinkrow.update(source=seed['id'],depth=seed['depth'],depth_delta=seed['depth']-sinkrow['inherited_depth'],edge_um=dist(seed['xy'],sinkrow['pin_xy']))
    return dict(schema='opentallas.kv_fault_reset_branch_candidate.v1',qualified_release=False,status='ADDITIVE_GEOMETRY_AND_SYMBOLIC_CLEAR_CANDIDATE',diagnostic_root_assert_skew_cycles=skew,required_sink_assert_depth=bound,targets=targets,stations=stations,source_clears=source_clears,source_loads=[dict(id=n['id'],root_id=k[0],clock=k[1],remaining=n['remaining']) for k,g in groups.items() for n in g if n['existing']],added_area_um2=len(stations)*CELL*CELL,max_edge_um=max([n['edge_um'] for n in stations]+[n['edge_um'] for n in targets]),max_branch_depth=max(t['depth'] for t in targets),old_loads_and_edges_unchanged=True,requirements=['Native same-family root epochs and assertion skew bound required; diagnostic skew is not a clock receipt','All new clock pins require native reach/phase/fanout/STA and physical reset branch views','Existing root outputs require native load timing with exact new fanout','Host reset and admission must include new assertion/release depths and POR flush; no old release changes','Functional cutoff and STATUS full path remain separate unqualified obligations'])

def main():
    p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);p.add_argument('--dir',type=Path,required=True);p.add_argument('--diagnostic-root-skew',type=int,required=True);a=p.parse_args()
    inv=json.loads((a.dir/'inventory.json').read_text());c=json.loads((a.dir/'candidate.json').read_text());m=json.loads((a.dir/'reset_loads.json').read_text())
    d=plan(a.run,inv,c,m,a.diagnostic_root_skew)
    d['input_hashes']={f:hashlib.sha256((a.dir/f).read_bytes()).hexdigest() for f in ('inventory.json','candidate.json','reset_loads.json')}
    (a.dir/'reset_branch_candidate.json').write_text(json.dumps(d,indent=1)+'\n')
    print(json.dumps({k:v for k,v in d.items() if k not in ('targets','stations','source_clears','source_loads')}))
if __name__=='__main__':main()
