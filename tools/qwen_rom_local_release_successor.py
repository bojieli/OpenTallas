#!/usr/bin/env python3
"""Constraint-derived local release successor. No RTL/map/numerical run.
Actual clock branches define groups and cloned local clock feeds. No assumed
zero clock skew, and no reset recovery/removal exception at synchronizer pins.
"""
import collections
import copy
import gzip
import json
import math
from pathlib import Path
import qwen_rom_local_release_context as H
R=H.R;M=H.M;N=H.N;G=H.G
OUT=Path('results/uarch/qwen_rom_local_release_successor_20261002')


def group_clock(b,original):
    g=b.g;coords=g['nominal_node_coordinates_um'];arcs=collections.defaultdict(list)
    for e in g['wire_edges']:arcs[e['driver']].append(e)
    sinkrows={r['instance']:r for r in g['source_clock_sinks']}
    ck,_,_=M.propagate(g,b.net,'ss',{g['root_driver']:{t:[0,0,5,5] for t in ('rise','fall')}})
    def describe(root,reg):
        paths={};pending=[(root,[])];nodes=set()
        while pending:
            n,path=pending.pop();nodes.add(n)
            for e in arcs[n]:
                if e['sink'] in sinkrows:paths[e['sink']]=path+[e]
                else:pending.append((e['sink'],path+[e]))
        vals=[ck[n+':'+sinkrows[n]['pin']]['rise'] for n in paths]
        return dict(root=root,region=reg,nodes=nodes,paths=paths,
            span=(max(v[1] for v in vals)-min(v[0] for v in vals)) if vals else 0,
            reset_targets=[p[-1] for n,p in paths.items() if n in g['reset_direct_sinks'] or n in g['metadata_reset_sinks']])
    groups=[];pending=[(q['root'],q['region']) for q in original]
    while pending:
        root,reg=pending.pop();q=describe(root,reg)
        # Source-measured branch spread selects an existing subtree, not a
        #parameter sweep.16ps leaves4ps of the unchanged20ps clock demand.
        if q['span']>16 and all(e['sink'] not in sinkrows for e in arcs[root]):
            live=[e['sink'] for e in arcs[root] if any(n in sinkrows for n in describe(e['sink'],reg)['paths'])]
            pending.extend((n,reg) for n in live)
        else:groups.append(q)
    assert set(n for q in groups for n in q['paths'])==set(sinkrows)
    assert sum(len(q['paths']) for q in groups)==len(sinkrows)
    return groups,arcs,ck


def construct():
    b,old,rows,direct,initial=H.load_clock();g=b.g;coords=g['nominal_node_coordinates_um']
    groups,arcs,ck=group_clock(b,initial)
    caps=R.library('ss')[2];roots={};source_clock=list(g['source_clock_sinks'])
    for i,q in enumerate(groups):
        root=q['root'];pos=coords[root]
        q['FFs']=[];q['cloned_clock_paths']=[]
        template=max(q['paths'],key=lambda n:ck[n+':'+next(r['pin'] for r in rows if r['instance']==n)]['rise'][1])
        path=q['paths'][template]
        for stage in range(2):
            ff=f'local_release_{i}.ff{stage}';q['FFs'].append(ff)
            b.net['cells'][ff]=dict(type=R.ASR,connections=dict(D=['ONE' if stage==0 else f'local_release_{i}.q0'],SETN=['ONE']))
            coords[ff]=[pos[0]+(-.54 if stage==0 else .54),pos[1]]
            driver=root;clones=[]
            for e in path[:-1]:
                node=b.buf(coords[e['sink']],'release_CLK_clone');b.edge(driver,node,'A',e['length_um']);clones.append(node)
                if driver!=root:
                    # Pay real isolation input loads of all unselected
                    #siblings. No imaginary capacitive loads or free cells.
                    olddriver=e['driver']
                    for sibling in arcs[olddriver]:
                        if sibling==e:continue
                        dummy=b.buf(coords[sibling['sink']],'release_CLK_dummy')
                        b.edge(driver,dummy,'A',sibling['length_um'])
                driver=node
            last=path[-1];original_cap=M.pin_cap(b.net['cells'][template]['type'],last['pin'],'ss')
            length=last['length_um']+(original_cap-caps[(R.ASR,'CLK')]['cap_fF'])/.165790
            if length<=0:raise ValueError('clock clone requires positive actual wire load')
            b.edge(driver,ff,'CLK',length)
            q['cloned_clock_paths'].append(dict(template=template,buffers=clones,last_wire_um=length))
            source_clock.append(dict(instance=ff,pin='CLK',cell=R.ASR,group='local_release_clock'))
        # Physical FF0 -> restored Q -> two finite hold buffers -> FF1 D.
        q['hold_entry']=b.buf(pos,'release_hold_entry');hold=b.buf(pos,'release_hold_second')
        g['added_primitive_cells'][q['hold_entry']]['connections']['A']=[f'local_release_{i}.q0']
        b.edge(q['hold_entry'],hold,'A',16);b.edge(hold,q['FFs'][1],'D',16)
        roots[root]=[r for r in source_clock if r['instance'] in q['paths'] or r['instance'] in q['FFs']]
    g['source_clock_sinks']=source_clock
    N.inverse_balance(b,roots)
    # Build the assertion collector after the complete clock load is sized.
    clockedges=copy.deepcopy(g['wire_edges']);incoming={e['sink']:e for e in clockedges if e['pin'] in ('A','CLK','clk')}
    ancestor=set()
    for q in groups:
        n=q['root']
        while n in incoming:
            e=incoming[n];ancestor.update((n,e['driver']));n=e['driver']
    for n in sorted(ancestor):
        name='assert_'+n;g['added_primitive_cells'][name]=dict(type=R.BUF,connections=dict(A=['PENDING'],Y=[b.bit]));b.bit+=1;coords[name]=coords[n]
    for e in clockedges:
        if e['driver'] in ancestor and e['sink'] in ancestor:b.edge('assert_'+e['driver'],'assert_'+e['sink'],'A',e['length_um'])
    localedges=collections.defaultdict(list)
    for e in clockedges:localedges[e['driver']].append(e)
    release=[]
    for i,q in enumerate(groups):
        root=q['root'];pos=coords[root]
        for ff in q['FFs']:b.edge('assert_'+root,ff,'RESETN',16)
        entry=b.buf(pos,'local_release_reset_entry');ack=b.buf(pos,'local_release_ACK_entry')
        g['added_primitive_cells'][entry]['connections']['A']=[f'local_release_{i}.q1']
        g['added_primitive_cells'][ack]['connections']['A']=[f'local_release_{i}.q1']
        required={e['sink'] for e in q['reset_targets']};nodes=set()
        for sink in required:
            n=sink
            while n in incoming and n!=root:e=incoming[n];nodes.add(e['driver']);n=e['driver']
        nodes.discard(root)
        for n in sorted(nodes):
            name='local_RST_'+n;g['added_primitive_cells'][name]=dict(type=R.BUF,connections=dict(A=['PENDING'],Y=[b.bit]));b.bit+=1;coords[name]=coords[n]
        for n in nodes|{root}:
            for e in localedges[n]:
                if e['sink'] not in nodes and e['sink'] not in required:continue
                a=entry if n==root else 'local_RST_'+n
                target='local_RST_'+e['sink'] if e['sink'] in nodes else e['sink']
                b.edge(a,target,'A' if e['sink'] in nodes else 'RESETN',e['length_um'])
        release.append(dict(group=i,root=root,region=q['region'],FFs=q['FFs'],reset_entry=entry,
            ACK_entry=ack,hold_entry=q['hold_entry'],reset_targets=sorted(required),cloned_clock_paths=q['cloned_clock_paths']))
    first='assert_'+g['root_driver'];pos=coords['context_provider'];target=coords[first]
    src=b.buf(pos,'local_assert_source');g['wire_edges'].append(dict(driver='context_provider',sink=src,pin='A',length_um=16))
    distance=max(16,sum(abs(x-y) for x,y in zip(pos,target)));count=math.ceil(distance/128);previous=src
    for i in range(1,count):
        n=b.buf([pos[d]+(target[d]-pos[d])*i/count for d in (0,1)],'local_assert_segment');b.edge(previous,n,'A',distance/count);previous=n
    b.edge(previous,first,'A',distance/count)
    g['local_release_groups']=release
    g['constraint_group_policy']='Existing subtree splits only where measured SS branch spread exceeds16ps; global demand remains20ps.'
    return b,old,rows,direct,groups


def generate():
    root=R.ROOT/OUT;root.mkdir(parents=True,exist_ok=True)
    if (root/'model-r1.json').exists() or (root/'model-r1.json.gz').exists():raise ValueError('preserve verdict')
    print('construct endpoint-matched local release clock paths',flush=True)
    b,old,rows,direct,groups=construct()
    print('price local raw/reset intervals',flush=True)
    timing=H.price(b)
    count=len(groups);region=collections.Counter(tuple(q['region']) for q in groups)
    gates=sum(R.tree_count(n,3)['buffers'] for n in region.values())+R.tree_count(len(region),3)['buffers']
    area=65983.07303971479+23.80914+1.44342+len(b.g['added_primitive_cells'])*.10206+count*2*(.37908+.04374)+gates*.08748+480*.10206+6*.10206
    report=dict(schema='QWEN_ENDPOINT_MATCHED_LOCAL_RELEASE_SUCCESSOR_R1',status='CONSTRUCTED_NOT_ADMITTED',
        groups=count,local_FFs=2*count,restoring_INV=2*count,clock_pins=102352+2*count,
        controlled_reset_pins=56683,local_raw_reset_pins=2*count,provider_FFs_separate=2,
        selected_map_sha256=M.MAP_SHA,selected_corridor_um=96.768,cell_ceiling_um2=125000,
        complete_reserved_cell_area_um2=area,timing=timing,
        SS_setup_uncertainty_ps=60,FF_hold_uncertainty_ps=25,nominal_clock_demand_ps=20,
        source_map_admission=False,PnR=False,additional_maps=0,numerical_runs=0,
        ACK_AND3_gate_reservation=gates,ACK_tracks_and_loads_complete=False,
        FF0_FF1_hold_buffers=2*count,internal_stage_setup_hold_qualified=False,
        legal_cell_sites_proven=False,pin_landings_proven=False,full_track_occupancy_proven=False,
        field1536_cell_area_mm2=area*1536/1e6,
        startup_ACK_observed_required=True,startup_once_not_per_layer_token=True,steady_added_cycles=0,
        original_reset_FAIL_records_preserved=True,
        epoch_abort='ACK invalidated on root reset; no launch until current owned request has all local ACKs and parent domain snapshot; accepted-owner interruption needs abort/quarantine receipt.')
    if any(v['controlled_reset_failures'] or v['raw_local_FF_reset_failures'] for v in timing.values()):report['status']='FAIL_ENDPOINT_MATCHED_LOCAL_RESET_INTERVAL'
    (root/'allocation-r1.json.gz').write_bytes(gzip.compress(R.canon(b.g),mtime=0))
    M.write(root/'model-r1.json',report)
    print(json.dumps({k:report[k] for k in ('status','groups','clock_pins','complete_reserved_cell_area_um2')},indent=2),flush=True)
    print({c:(v['controlled_reset_failures'],v['raw_local_FF_reset_failures'],v['source_endpoint_clock_skew_ps']) for c,v in timing.items()},flush=True)


if __name__=='__main__':generate()
