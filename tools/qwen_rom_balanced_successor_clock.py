#!/usr/bin/env python3
"""One finite equal-depth clock construction, on the selected successor only.
Analytical common-source slew is correlated, never subtracted as unrelated
arrival uncertainty. Actual extraction, macro/data timing and cuts remain gates.
"""
import functools
import gzip
import hashlib
import json
import math
from pathlib import Path
import qwen_rom_retention_parent_launch as L
R=L.R
M=L.M
S=L.S
OUT=Path('results/uarch/qwen_rom_balanced_successor_clock_20261002')
R.envelope=functools.lru_cache(maxsize=8192)(R.envelope)


def morton(pos):
    x=int(pos[0]/357.696*65535);y=int(pos[1]/1360.8*65535)
    return sum(((x>>i)&1)<<(2*i) | ((y>>i)&1)<<(2*i+1) for i in range(16))


def construct():
    old=json.loads(gzip.decompress((R.ROOT/S.OUT/'successor-allocation-r1.json.gz').read_bytes()))
    rows=json.loads(gzip.decompress((R.ROOT/R.OUT/'mapped-sink-census-r1.json.gz').read_bytes()))
    removed=set(old['removed_old_control_FFs'])
    rows=[r for r in rows if r['group'] in ('logic_clock','ROM_clock','KV_clock') and r['instance'] not in removed]
    rows += [dict(instance=r['instance'],pin='CLK',cell=R.ASR,group='successor_control_clock') for r in old['source_control_cells']]
    if len(rows)!=102352:raise ValueError('wrong successor clock inventory')
    rows.append(dict(instance='context_provider',pin='clk_stream',cell='ot_qwen_rom_reset_parent_provider',group='two_provider_FFs'))
    coords={r['instance']:old['nominal_node_coordinates_um'][r['instance']] for r in rows}
    originals={r['instance']:dict(type=r['cell'],connections={}) for r in rows}
    cells={};edges=[];bit=1;levels=[]
    def buf(name,pos):
        nonlocal bit
        cells[name]=dict(type=R.BUF,connections=dict(A=['PENDING'],Y=[bit]));coords[name]=pos;bit+=1
    def edge(driver,sink,pin,length):
        dest=cells[sink] if sink in cells else originals[sink]
        dest['connections'][pin]=cells[driver]['connections']['Y'][:]
        edges.append(dict(driver=driver,sink=sink,pin=pin,length_um=length,
            meander_um=max(0,length-sum(abs(a-b) for a,b in zip(coords[driver],coords[sink])))))
    targets=[(r['instance'],r['pin']) for r in sorted(rows,key=lambda r:morton(coords[r['instance']]))]
    level=0
    while True:
        groups=[]
        for i in range(0,len(targets),8):
            children=targets[i:i+8]
            center=[sum(coords[n][d] for n,p in children)/len(children) for d in (0,1)]
            name=f'balanced_L{level}_{i//8}';buf(name,center);groups.append((name,children))
        distance=max(16,max(sum(abs(a-b) for a,b in zip(coords[n],coords[c])) for n,cs in groups for c,p in cs))
        maxcap=max(M.pin_cap(originals[n]['type'],p,'ss') for n,p in targets) if level==0 else M.pin_cap(R.BUF,'A','ss')
        pad=max((maxcap-M.pin_cap(originals[n]['type'],p,'ss'))/.165790 for n,p in targets) if level==0 else 0
        segments=math.ceil(distance/(128-pad))
        length=distance/segments
        for name,children in groups:
            # Every parent sees exactly eight matched isolation inputs.
            for i in range(8):
                branch=name+'.isolate'+str(i);buf(branch,coords[name]);edge(name,branch,'A',16)
                if i>=len(children):continue # paid terminal dummy BUF input
                child,pin=children[i];start=coords[name];end=coords[child];previous=branch
                for j in range(1,segments):
                    n=branch+'.segment'+str(j);buf(n,[start[d]+(end[d]-start[d])*j/segments for d in (0,1)])
                    edge(previous,n,'A',length);previous=n
                last=length+(maxcap-M.pin_cap(originals[child]['type'],pin,'ss'))/.165790 if level==0 else length
                edge(previous,child,pin,last)
        levels.append(dict(level=level,nodes=len(groups),uniform_route_budget_um=distance,
            route_segments=segments,max_terminal_cap_equalization_um=pad))
        targets=[(n,'A') for n,cs in groups]
        if len(targets)==1:root=targets[0][0];break
        level+=1
    cells[root]['connections']['A']=['PRIMARY_CLOCK_SOURCE']
    return dict(added_primitive_cells=cells,original_cell_pin_edits={},wire_edges=edges,nominal_node_coordinates_um=coords,
        root_driver=root,clock_sinks=rows,levels_leaf_to_root=levels,geometry_is_analytical=True,
        meanders_are_length_reservations_not_routed_wires=True),dict(cells=originals)


def main():
    out=R.ROOT/OUT;out.mkdir(parents=True,exist_ok=True)
    if (out/'model-r1.json').exists():raise ValueError('preserve verdict')
    g,net=construct();reports={}
    for corner in ('ss','ff'):
        scenarios=[]
        for slew in (5,80):
            states,_,loads=M.propagate(g,net,corner,{g['root_driver']:{t:[0,0,slew,slew] for t in ('rise','fall')}})
            waves=[states[r['instance']+':'+r['pin']]['rise'] for r in g['clock_sinks']]
            lo=min(w[0] for w in waves);hi=max(w[1] for w in waves)
            scenarios.append(dict(common_primary_clock_slew_ps=slew,arrival_minmax_ps=[lo,hi],same_source_skew_ps=hi-lo,
                provider_clock=states['context_provider:clk_stream']['rise'],max_BUF_cap_fF=max(loads.values()),
                max_slew_ps=max(w[3] for w in waves)))
        reports[corner]=dict(scenarios=scenarios,worst_same_source_skew_ps=max(s['same_source_skew_ps'] for s in scenarios),
            demanded_skew_ps=20,endpoint_slew_scenario_proof_only=True,
            continuous_source_slew_and_extracted_skew_qualified=False)
    coords=g['nominal_node_coordinates_um'];cuts={}
    for axis,limits in ((0,(130.464,227.232)),(1,(393.12,489.888))):
        for line in limits:
            count=sum(min(coords[e['driver']][axis],coords[e['sink']][axis])<line<=max(coords[e['driver']][axis],coords[e['sink']][axis]) for e in g['wire_edges'])
            cuts[f'{axis}:{line}']=dict(monotone_geometric_crossings=count,clock_reserved_tracks=64,
                meander_routes_qualified=False,monotone_lower_bound_fits=count<=64)
    payload=gzip.compress(R.canon(g),mtime=0);(out/'balanced-clock-allocation-r1.json.gz').write_bytes(payload)
    parent=R.obj(L.OUT/'model-r1.json');area=parent['conservative_reserved_area_um2']+len(g['added_primitive_cells'])*.10206
    result=dict(schema='QWEN_ONE_BALANCED_SUCCESSOR_CLOCK_V1',status='CONSTRUCTION_ONLY_CONTEXT_ADMISSION_OPEN',
        selected_map_sha256=M.MAP_SHA,source_successor_sha256=parent['retained_source_sha256'],
        successor_clock_ports=102352,additional_provider_clock_FFs=2,physical_clock_pins=102354,
        successor_reset_pins=56683,selected_corridor_um=96.768,cell_ceiling_um2=125000,
        paid_clock_buffers=len(g['added_primitive_cells']),paid_clock_buffer_area_um2=len(g['added_primitive_cells'])*.10206,
        conservative_area_retaining_old_reservations_um2=area,conservative_area_fits=area<=125000,
        total_wire_length_um=sum(e['length_um'] for e in g['wire_edges']),
        total_meander_reservation_um=sum(e['meander_um'] for e in g['wire_edges']),
        levels=g['levels_leaf_to_root'],clock_price=reports,corridor_cuts=cuts,
        failed_unbalanced_evidence_preserved=[str(M.OUT/'model-r1.json'),str(S.OUT/'model-r1.json'),str(L.OUT/'model-r1.json')],
        reset_startup_reprice='Required on this exact new clock construction; former66SS/8FF failures remain history. No prior phases or launch windows transferred.',
        binary_init_admission='Still requires source-reachable owned binary/reset/read/tag proof; Euclid storedZFAIL retained.',
        next_gate='Resolve corridor cuts/meander placement and continuous-source skew; allocate matching reset, launch, and startup/barrier on these endpoints before source-map admission.',
        installed_CTS_precondition=False,source_map_admission=False,PnR=False,numerical_runs=0,additional_maps=0,
        allocation_sha256=hashlib.sha256(payload).hexdigest())
    if any(r['worst_same_source_skew_ps']>20 for r in reports.values()):result['status']='FAIL_BALANCED_CONSTRUCTION_SKEW_DEMAND'
    if not all(c['monotone_lower_bound_fits'] for c in cuts.values()):result['status']='FAIL_BALANCED_CONSTRUCTION_CORRIDOR_CUTS'
    if area>125000:result['status']='FAIL_BALANCED_CONSTRUCTION_CELL_CEILING'
    M.write(out/'model-r1.json',result)
    paths=[Path(__file__).relative_to(R.ROOT),Path('tests/test_qwen_rom_balanced_successor_clock.py'),S.OUT/'sourcepins-r1.json',L.OUT/'sourcepins-r1.json',L.OUT/'model-r1.json',S.OUT/'successor-allocation-r1.json.gz',R.OUT/'mapped-sink-census-r1.json.gz']
    M.write(out/'sourcepins-r1.json',dict(sha256={str(p):M.digest(p) for p in paths}))
    M.write(out/'artifact-sha256-r1.json',{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.iterdir() if p.is_file() and p.name!='artifact-sha256-r1.json'})
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
