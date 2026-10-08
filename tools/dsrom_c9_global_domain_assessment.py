#!/usr/bin/env python3
"""Necessary two-ended domains and conservative exact-component assessment.
No SAT search, placement selection, or mutation of the live solver.
"""
import bisect, collections, gzip, hashlib, json, math
from fractions import Fraction as F
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
INPUT=ROOT/'results/uarch/dsrom_c9_global_native_constraints_20261003/inputs'
OUT=ROOT/'results/uarch/dsrom_c9_global_domain_assessment_20261003'

def node_box(t,j,rc):
    # A_j = source + j*(Y-A) + sum(first j+1 edge displacements).
    # sink = A_j + (n-j)*(Y-A) + sum(remaining n-j edges).
    n=len(t['node_ids']);left=F(str(t['first_metal_budget_fF']))+j*F('2.88')
    right=(n-j)*F('2.88');sx,sy=t['source_contact_DBU'];tx,ty=t['sink_contact_DBU']
    cx,cy=(F(str(rc[k]))/1000 for k in ('M8','M9'))
    return [math.ceil(max(F(sx)+j*321-left/cx,F(tx)-(n-j)*321-right/cx)),
            math.ceil(max(F(sy)-left/cy,F(ty)-right/cy)),
            math.floor(min(F(sx)+j*321+left/cx,F(tx)-(n-j)*321+right/cx)),
            math.floor(min(F(sy)+left/cy,F(ty)+right/cy))]

class DSU:
    def __init__(self,n):self.p=list(range(n))
    def find(self,i):
        while self.p[i]!=i:self.p[i]=self.p[self.p[i]];i=self.p[i]
        return i
    def union(self,a,b):self.p[self.find(a)]=self.find(b)

def assess(p):
    rc=p['RC_fF_per_um'];rows=collections.defaultdict(list)
    for site in p['sites']:
        x,y=site['bbox_DBU'][:2];rows[y+135].append(x+27)
    rows={y:sorted(xs) for y,xs in rows.items()};ys=sorted(rows)
    intervals=collections.defaultdict(list);bounds=[];empty=[];domain_sizes=[];direct=[]
    tasks=p['tasks'];ds=DSU(len(tasks));edges=0
    for ti,t in enumerate(tasks):
        n=len(t['node_ids']);edges+=n+1
        if not n:
            a=t['source_contact_DBU'];b=t['sink_contact_DBU']
            c=sum(abs(a[i]-b[i])*F(str(rc[k]))/1000 for i,k in enumerate(('M8','M9')))
            if c>F(str(t['first_metal_budget_fF'])):direct.append(dict(task=ti,C_fF=str(c),budget=t['first_metal_budget_fF']))
            continue
        boxes=[]
        for j,node in enumerate(t['node_ids']):
            box=node_box(t,j,rc);boxes.append(box);count=0
            for y in ys[bisect.bisect_left(ys,box[1]):bisect.bisect_right(ys,box[3])]:
                count+=max(0,bisect.bisect_right(rows[y],box[2])-bisect.bisect_left(rows[y],box[0]))
            bounds.append(dict(node=node,task=ti,ordinal=j,necessary_A_bbox_DBU=box,rectangle_site_domain_count=count))
            domain_sizes.append(count)
            if count==0:empty.append(dict(node=node,task=ti,bbox=box))
        # One envelope per branch over-merges domains but never misses a
        # shared-site constraint. Branch edge factors stay within component.
        box=[min(b[0] for b in boxes),min(b[1] for b in boxes),max(b[2] for b in boxes),max(b[3] for b in boxes)]
        for y in ys[bisect.bisect_left(ys,box[1]):bisect.bisect_right(ys,box[3])]:
            lo=bisect.bisect_left(rows[y],box[0]);hi=bisect.bisect_right(rows[y],box[2])-1
            if lo<=hi:intervals[y].append((lo,hi,ti))
    # Only join overlapping intervals if an actual candidate site is shared.
    # This retains injectivity; no geographic bin boundary is assumed safe.
    for iv in intervals.values():
        iv.sort();end=-1;owner=None
        for lo,hi,ti in iv:
            if lo<=end:ds.union(owner,ti);end=max(end,hi)
            else:owner=ti;end=hi
    comps=collections.defaultdict(lambda:dict(nodes=0,tasks=0,envelope_sites=0))
    for ti,t in enumerate(tasks):
        if t['node_ids']:
            c=comps[ds.find(ti)];c['nodes']+=len(t['node_ids']);c['tasks']+=1
    for iv in intervals.values():
        by=collections.defaultdict(list)
        for lo,hi,ti in iv:by[ds.find(ti)].append((lo,hi))
        for root,ranges in by.items():
            end=-1
            for lo,hi in sorted(ranges):
                comps[root]['envelope_sites']+=max(0,hi-max(end,lo-1));end=max(end,hi)
    sizes=sorted(domain_sizes)
    summary=dict(shard=p['shard'],fixed_nodes=p['node_count'],tasks=len(tasks),all_edges=edges,
        candidate_sites=len(p['sites']),rectangular_domain_empty_witnesses=empty,direct_edge_failures=direct,
        domain_site_count=dict(min=min(sizes),median=sizes[len(sizes)//2],max=max(sizes),sum=sum(sizes),unpruned_sum=p['node_count']*len(p['sites'])),
        conservative_components=sorted(comps.values(),key=lambda c:-c['nodes']),
        component_Hall_deficits=[c for c in comps.values() if c['nodes']>c['envelope_sites']],
        domain_scope='Canonical e137 contacts only; rectangles are necessary outer bounds, not arc-consistent domains or native physical routes',
        unsat_witness_found=bool(empty or direct or any(c['nodes']>c['envelope_sites'] for c in comps.values())))
    assert len(bounds)==p['node_count'] and sum(c['nodes'] for c in comps.values())==p['node_count']
    return summary,bounds

def build():
    OUT.mkdir(parents=True,exist_ok=True);cases={};pins={}
    for s in (0,1):
        path=INPUT/f'global_shard{s}_problem.json.gz';raw=path.read_bytes();p=json.loads(gzip.decompress(raw));summary,bounds=assess(p)
        pins[str(s)]=hashlib.sha256(raw).hexdigest();cases[str(s)]=summary
        data=''.join(json.dumps(b,sort_keys=True,separators=(',',':'))+'\n' for b in bounds).encode()
        (OUT/f'shard{s}_necessary_domains.jsonl.gz').write_bytes(gzip.compress(data,mtime=0))
        print(json.dumps(summary,sort_keys=True),flush=True)
    m=dict(source_global_problem_commit='e13772e074b8acae0552a275dc08b3b06299c00d',source_problem_sha256=pins,cases=cases,
        live_solver_unchanged=True,second_solver_launched=False,physical_build_admitted=False,
        exact_split='Shards have disjoint sites and constraints in frozen e137 allocation encoding; shared upstream clock/PG remain contextual obligations',
        native_successor='Recompute domains with finite native A/Y endpoint pairs; keep one output contact per shared physical source and mutual via/escape/PG exclusions. Native contacts are not equivalent to canonical y135.',
        next_algorithm='Within each safe component: rational two-ended diamond pruning; forward/backward support across complete chain; all-different matching/Hall propagation; shared source contact factors; cutset/branch search only with boundary constraints retained. Independent branch placement alone is invalid.')
    (OUT/'model.json').write_text(json.dumps(m,indent=2,sort_keys=True)+'\n')
    return m
if __name__=='__main__':build()
