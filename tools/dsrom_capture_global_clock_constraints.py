#!/usr/bin/env python3
"""One simultaneous fixed-count graph/site problem. No locked first hops.

SAT describes this native-contact geometric problem only. Upstream waveforms,
upper-layer occupancy, supply current and full-context SS/FF are separate gates.
"""
import argparse,gzip,hashlib,json,math,os
from pathlib import Path
from fractions import Fraction
import z3
import dsrom_capture_clock_selected_union as C
import dsrom_capture_clock_branch_reallocation as R
import dsrom_capture_completion_hook_slot as H
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'results/uarch/dsrom_capture_global_clock_constraints_20261003'

def topology(branches):
    graph={};depth={};pads={}
    for b in branches:graph.setdefault(b['source'],[]).append(b)
    def visit(name):
        if name not in graph:return 0
        if name in depth:return depth[name]
        terms=[b['proposed_relay_BUF']+1+visit(b['destination']) for b in graph[name]];depth[name]=max(terms)
        for b,t in zip(graph[name],terms):pads[(b['net'],b['destination'])]=depth[name]-t
        return depth[name]
    for name in graph:visit(name)
    return pads,depth

def contact(pin,via):
    # Fixed canonical enclosed contact, never the optimistic pin rectangle gap.
    sx,sy=pin['point_DBU'];options=[]
    for r in pin['literal_rectangles']:
        if r['layer']!='M1':continue
        a,b,A,B=r['bbox_DBU'];lo=a-via[0];hi=A-via[2];bottom=b-via[1];top=B-via[3]
        if lo>hi or bottom>top:continue
        x=min(hi,max(lo,round(sx)));y=min(top,max(bottom,round(sy)));options.append((abs(x-sx)+abs(y-sy),x,y))
    if not options:raise ValueError('No enclosed native VIA12 contact')
    _,x,y=min(options);return [x,y]

def dump(p,obj):p.write_bytes(gzip.compress((json.dumps(obj,sort_keys=True,separators=(',',':'))+'\n').encode(),mtime=0))
def load(p):return json.loads(gzip.decompress(p.read_bytes()))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def problem(out):
    origins=json.loads((BASE/'inputs/origins.json').read_text())
    for row in origins:
        if sha(BASE/'inputs'/row['copy'])!=row['sha256']:raise ValueError('failed source drift')
    d=C.inputs();arch=d['model.json'];old=json.loads((C.BASE/'model.json').read_text());grid=R.tech();via=next(p['bbox'] for p in grid['tech_via_definitions']['VIA12'] if p['layer']=='M1')
    hd,_=C.H.H.inputs();lef=hd['cell_LEF.json']['BUFx4_ASAP7_75t_R'];hook=H.build();identity=C.I.build();out.mkdir(parents=True,exist_ok=True);cases={}
    for s in (0,1):
        raw=arch['physical_shards'][str(s)];existing=d[f'shard{s}_cells.jsonl.gz'];common=raw['shifted_control_bbox_DBU'];patch=[common[0],common[1],common[0]+8640,common[1]+5400]
        local_hook=hook['gross_hook_cells'] if s==0 else [];local_identity=identity['source_cell_proposal'] if s==0 else []
        exclusions=existing+local_hook+local_identity
        # Full retained legal raw MX pool; common R0/MX rows, same known PG phase.
        sites=R.candidates(raw['raw_slot_bbox_DBU'],exclusions,s)
        for y in range(patch[1],patch[3],270):
            for x in range(patch[0],patch[2]-378+1,378):
                b=[x,y,x+378,y+270]
                if any(R.overlap(b,p['bbox_DBU']) for p in exclusions if patch[0]<=p['bbox_DBU'][0]<patch[2] and patch[1]<=p['bbox_DBU'][1]<patch[3]):continue
                sites.append(dict(proposed_site_ID=f's{s}.common.{x}.{y}',bbox_DBU=b,orientation='R0' if (y-patch[1])%540==0 else 'MX',home='common',master='BUFx4_ASAP7_75t_R'))
        # Every chosen A/Y centre encloses the actual VIA12 metal landing.
        for site in sites:
            for pin,px in [('A',27),('Y',348)]:
                x,y=site['bbox_DBU'][:2];landing=[x+px+via[0],y+135+via[1],x+px+via[2],y+135+via[3]]
                if not any(R.E.contained(landing,R.E.transform(r,site)) for r in R.E.shapes(lef,pin)):raise ValueError('Illegal canonical contact')
        branches=json.loads(gzip.decompress((C.BASE/f'shard{s}_clock_branches.json.gz').read_bytes()));pads,depth=topology(branches);nets={n['name']:n for n in d[f'shard{s}_clock_nets.jsonl.gz']};tasks=[];nextid=0;outside=0
        for b in branches:
            n=b['proposed_relay_BUF']+pads[(b['net'],b['destination'])]
            net=nets[b['net']];sink=next(v for v in net['sinks'] if v['instance']==b['destination']);src=contact(net['source'],via);dst=contact(sink,via)
            budget=b['first_driver_total_wire_budget_fF']/2/b['source_fanout']
            ids=list(range(nextid,nextid+n));nextid+=n
            tasks.append(dict(source_instance=b['source'],destination=b['destination'],net=b['net'],node_ids=ids,source_contact_DBU=src,sink_contact_DBU=dst,first_metal_budget_fF=budget,relay_metal_budget_fF=2.88,source_fanout=b['source_fanout'],relay_count=b['proposed_relay_BUF'],pad_count=pads[(b['net'],b['destination'])],source_pin=net['source'],sink_pin=sink))
            if n:
                r=raw['raw_slot_bbox_DBU'];rc=old['restricted_route_family_RC_fF_per_um'];lower=(max(0,r[0]-src[0],src[0]-r[2])*rc['M8']+max(0,r[1]-src[1],src[1]-r[3])*rc['M9'])/1000
                outside+=lower>budget
        expected=old['raw_empty_row_correction_site_inventories'][s]['requested_sites']
        if nextid!=expected:raise ValueError('Fixed correction count drift')
        # Unchanged original fanout graph includes zero-insertion direct edges.
        p=dict(shard=s,sites=sites,tasks=tasks,node_count=nextid,RC_fF_per_um=old['restricted_route_family_RC_fF_per_um'],VIA12_M1=via,source_literal_raw_PG=raw['PG_M1_literal_rails'],common_prefix_patch_DBU=patch,source_root_input=raw['raw_clock_root_input'],hook=local_hook,identity=local_identity,upstream_root_driver=None,common_control_reset_ingress=None,supply_current_provider=None)
        file=out/f'shard{s}_problem.json.gz';dump(file,p)
        cases[str(s)]=dict(nodes=nextid,branches=len(tasks),pad_only_branches=sum(t['relay_count']==0 and bool(t['node_ids']) for t in tasks),legal_nonoverlap_candidate_sites=len(sites),minimum_outside_raw_enclosed_contact_first_nodes=outside,file=file.name,sha256=sha(file),root=raw['raw_clock_root_input'])
    result=dict(candidate=old['candidate'],problem='ONE_SAMECOUNT_GLOBAL_BRANCH_CONTACT_SITE_ALLOCATION',source_failures=origins,cases=cases,counts=[38383,30231],nodes=68614,selected_bank=old['selected_selector_clock_construction'],annex_charge_mm2=0,locked_first_hops=False,greedy_assignment_used=False,all_nodes_simultaneous=True,physical_build_admitted=False,placement_verdict='NOT_SOLVED',missing_parent_bindings=['root driver literal Y/clock arrival,slew,skew; common/reset full sink identities and release','complete upper-layer OBS/contact/coupling occupancy and finite supply upfeed current','current PHW10 F/read/R+2 callbacks for absolute consumer/capacity model'],new_hardware_jobs=[])
    (out/'model.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n');return result

def encoding(problems):
    solver=z3.Solver();vars={}
    # Immutable shared coordinate tables; no anonymous movable source parents.
    for p in problems:
        s=p['shard'];sites=p['sites'];AX=z3.Array(f's{s}_AX',z3.IntSort(),z3.IntSort());AY=z3.Array(f's{s}_AY',z3.IntSort(),z3.IntSort())
        for i,site in enumerate(sites):
            x,y=site['bbox_DBU'][:2];solver.add(z3.Select(AX,i)==x+27,z3.Select(AY,i)==y+135)
        ids=[z3.Int(f's{s}_station_{i}') for i in range(p['node_count'])];vars[s]=ids
        # Injective owner array enforces distinct sites without materializing
        # O(N^2) pairwise arithmetic inequalities for 68614 nodes.
        owner=z3.Array(f's{s}_site_owner',z3.IntSort(),z3.IntSort())
        for i,v in enumerate(ids):solver.add(z3.Select(owner,v)==i)
        for i in ids:solver.add(i>=0,i<len(sites))
        X=lambda i:z3.Select(AX,ids[i]);Y=lambda i:z3.Select(AY,ids[i])
        rc={k:z3.RealVal(str(v)) for k,v in p['RC_fF_per_um'].items()}
        def bound(a,b,budget):
            dx=a[0]-b[0];dy=a[1]-b[1]
            solver.add((z3.If(dx>=0,dx,-dx)*rc['M8']+z3.If(dy>=0,dy,-dy)*rc['M9'])<=z3.RealVal(str(budget))*1000)
        for t in p['tasks']:
            chain=t['node_ids'];source=t['source_contact_DBU']
            for j,i in enumerate(chain):
                target=[X(i),Y(i)];bound(source,target,t['first_metal_budget_fF'] if j==0 else 2.88);source=[X(i)+321,Y(i)]
            bound(source,t['sink_contact_DBU'],2.88 if chain else t['first_metal_budget_fF'])
    return solver,vars

def audit_assignment(p,assignment):
    if len(assignment)!=p['node_count'] or {v['node'] for v in assignment}!=set(range(p['node_count'])):raise ValueError('All fixed nodes required once')
    legal={(tuple(v['bbox_DBU']),v['orientation']) for v in p['sites']};used=set();nodes={v['node']:v for v in assignment}
    for v in assignment:
        key=(tuple(v['bbox_DBU']),v['orientation'])
        if key not in legal or key in used:raise ValueError('Illegal/overlapping original or shared site')
        used.add(key)
    rc={k:Fraction(str(v)) for k,v in p['RC_fF_per_um'].items()};checked=0
    def edge(a,b,budget):
        nonlocal checked
        value=(abs(a[0]-b[0])*rc['M8']+abs(a[1]-b[1])*rc['M9'])/1000
        if value>Fraction(str(budget)):raise ValueError('Actual contact metal budget violated')
        checked+=1
    for t in p['tasks']:
        source=t['source_contact_DBU']
        for j,i in enumerate(t['node_ids']):
            x,y=nodes[i]['bbox_DBU'][:2];edge(source,[x+27,y+135],t['first_metal_budget_fF'] if j==0 else 2.88);source=[x+348,y+135]
        edge(source,t['sink_contact_DBU'],2.88 if t['node_ids'] else t['first_metal_budget_fF'])
    return dict(nodes=len(nodes),all_enclosed_contact_edges_checked=checked,geometric_constraints_pass=True,physical_build_admitted=False)

def solve(path,out):
    out.mkdir(parents=True,exist_ok=True)
    if (out/'progress.json').exists() or (out/'result.json').exists():raise ValueError('Never overwrite a search attempt')
    ps=[load(path/f'shard{s}_problem.json.gz') for s in (0,1)]
    (out/'progress.json').write_text(json.dumps({'phase':'ENCODING_SINGLE_FULL_PROBLEM','PID':os.getpid(),'nodes':sum(p['node_count'] for p in ps),'z3_version':z3.get_version_string(),'no_timeout_or_random_sweep':True,'physical_build_admitted':False},indent=2)+'\n')
    print('ENCODING_SINGLE_FULL_PROBLEM',os.getpid(),flush=True)
    solver,ids=encoding(ps)
    (out/'progress.json').write_text(json.dumps({'phase':'ALL_68614_NODES_ENCODED_SEARCH_PENDING','constraints':len(solver.assertions()),'variables':sum(len(v) for v in ids.values()),'no_timeout_or_random_sweep':True,'physical_build_admitted':False},indent=2)+'\n')
    print('ALL_68614_NODES_ENCODED_SEARCH_PENDING',len(solver.assertions()),flush=True)
    status=solver.check();result=dict(status=str(status),source_problem_sha256={s:sha(path/f'shard{s}_problem.json.gz') for s in (0,1)},physical_build_admitted=False,scope='Canonical enclosed contacts and the complete fixed legal cell pool. SAT is not upper-layer route, power, reset or SSFF closure; UNSAT is not architectural impossibility.')
    if status==z3.sat:
        model=solver.model()
        result['independent_assignment_audits']={}
        for p in ps:
            chosen=[dict(node=i,**p['sites'][model.eval(v).as_long()]) for i,v in enumerate(ids[p['shard']])]
            result['independent_assignment_audits'][str(p['shard'])]=audit_assignment(p,chosen)
            dump(out/f'shard{p["shard"]}_complete_sites.json.gz',chosen)
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result
if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--out',type=Path,required=True);a.add_argument('--solve',type=Path);args=a.parse_args()
    m=solve(args.solve,args.out) if args.solve else problem(args.out);print(json.dumps({k:v for k,v in m.items() if k not in ('source_failures','cases','selected_bank')},indent=2))
