#!/usr/bin/env python3
"""Single corridor-aligned collector and matched metadata reset successor.
Preserves rejected local/global constructions; never invokes a hardware build.
"""
import collections
import copy
import gzip
import json
import math
from pathlib import Path
import qwen_rom_local_subtree_context as N
R=N.R;M=N.M
OUT=Path('results/uarch/qwen_rom_regional_collector_context_20261002')
BOUNDS=([0.,130.464,227.232,357.696],[0.,393.12,489.888,1360.8])


def region(pos):
    return tuple(next(i for i in range(3) if v<bounds[i+1] or i==2)
                 for v,bounds in zip(pos,BOUNDS))


def construct():
    old,rows,direct=N.inventory();b=N.Builder(old,rows);coords=b.g['nominal_node_coordinates_um']
    groups=collections.defaultdict(list)
    for r in rows:
        pos=coords[r['instance']];reg=region(pos)
        # Bins start at each actual corridor boundary. No local branch or
        #balancing coil may straddle any of the four admission cuts.
        local=tuple(int((v-BOUNDS[d][reg[d]])/size) for d,(v,size) in enumerate(zip(pos,(44.712,42.525))))
        groups[reg+local+(r['cell'],)].append(r)
    roots={};regional=collections.defaultdict(list);ledger=[]
    for key,targets in sorted(groups.items()):
        root,depth=b.tree([(r['instance'],r['pin']) for r in targets],'local_leaf',4)
        roots[root]=targets;regional[key[:2]].append((root,'A'))
        ledger.append(dict(root=root,region=list(key[:2]),bin=list(key[2:4]),sinks=len(targets),levels=depth))
    collectors=[]
    for reg,targets in sorted(regional.items()):
        root,depth=b.tree(targets,'regional_collector',1)
        collectors.append((root,'A'))
    hub,depth=b.tree(collectors,'global_regional_hub',1)
    entry=b.buf([178.848,393.12],'regional_clock_entry')
    distance=max(16,sum(abs(x-y) for x,y in zip(coords[entry],coords[hub])))
    count=math.ceil(distance/128);previous=entry
    for i in range(1,count):
        name=b.buf([coords[entry][d]+(coords[hub][d]-coords[entry][d])*i/count for d in (0,1)],'regional_clock_input')
        b.edge(previous,name,'A',distance/count);previous=name
    b.edge(previous,hub,'A',distance/count)
    b.g['added_primitive_cells'][entry]['connections']['A']=['PRIMARY_CLOCK_SOURCE']
    b.g.update(root_driver=entry,source_clock_sinks=rows,local_group_ledger=ledger,
               local_bin_um=[44.712,42.525],regional_collector_roots=collectors,
               global_equalization_chain_duplicated=False)
    N.inverse_balance(b,roots)
    return b,old,rows,direct


def matched_reset(b,old,rows,direct):
    g=b.g;coords=g['nominal_node_coordinates_um'];clockcells=set(g['added_primitive_cells']);edges=copy.deepcopy(g['wire_edges'])
    metadata=[r['instance'] for r in old['source_control_cells']]
    census=json.loads(gzip.decompress((R.ROOT/R.OUT/'mapped-sink-census-r1.json.gz').read_bytes()))
    metadata += [r['instance'] for r in census if r['group']=='distributed_reset' and r['instance'] not in old['removed_old_control_FFs']]
    reset=set(direct)|set(metadata)
    assert len(reset)==56683 and len(metadata)==90
    for name in clockcells:
        new='reset_'+name;g['added_primitive_cells'][new]=dict(type=R.BUF,connections=dict(A=['PENDING'],Y=[b.bit]));b.bit+=1;coords[new]=coords[name]
    for e in edges:
        if e['sink'] not in clockcells and e['sink'] not in reset:continue
        b.edge('reset_'+e['driver'],'reset_'+e['sink'] if e['sink'] in clockcells else e['sink'],
               'A' if e['sink'] in clockcells else 'RESETN',e['length_um'])
    root='reset_'+g['root_driver'];pos=coords['context_provider'];end=coords[root]
    branch=b.buf(pos,'local_reset_source');g['wire_edges'].append(dict(driver='context_provider',sink=branch,pin='A',length_um=16,meander_um=16))
    distance=max(16,sum(abs(x-y) for x,y in zip(pos,end)));count=math.ceil(distance/128);previous=branch
    for i in range(1,count):
        name=b.buf([pos[d]+(end[d]-pos[d])*i/count for d in (0,1)],'local_reset_source_segment');b.edge(previous,name,'A',distance/count);previous=name
    b.edge(previous,root,'A',distance/count)
    # Exact external root feed and both actual raw-reset combinational
    #controls survive. Old15 metadata BUFs stay area-paid in the mapped
    #subtotal, but this successor redirects metadata RESETN leaf ports.
    wanted=[('context_provider','external_reset_n')]+[(r['instance'],r['pin']) for r in old['reset_combinational_controls']]
    incoming={(e['sink'],e['pin']):e for e in old['wire_edges']};kept={}
    while wanted:
        n,p=wanted.pop()
        if (n,p) not in incoming:continue
        e=incoming[n,p];kept[n,p]=e
        if e['driver']!='context_provider':wanted.append((e['driver'],'A'))
    for e in kept.values():
        for name in (e['driver'],e['sink']):
            if name in coords:continue
            coords[name]=old['nominal_node_coordinates_um'][name]
            if name in old['added_primitive_cells']:g['added_primitive_cells'][name]=copy.deepcopy(old['added_primitive_cells'][name])
            else:
                typ=next(r['cell'] for r in old['reset_combinational_controls'] if r['instance']==name)
                b.net['cells'][name]=dict(type=typ,connections={})
        g['wire_edges'].append(copy.deepcopy(e))
    g.update(reset_direct_sinks=sorted(direct),metadata_reset_sinks=metadata,
             clock_buffer_count=len(clockcells),reset_mirror_buffer_count=len(clockcells),
             redirected_metadata_RESETN_ports=sorted(metadata))


def cuts(g):
    coords=g['nominal_node_coordinates_um'];out={}
    for axis,bounds in enumerate(BOUNDS):
        for line in bounds[1:-1]:
            witnesses=[]
            for e in g['wire_edges']:
                a=coords[e['driver']];b=coords[e['sink']]
                if min(a[axis],b[axis])<line<=max(a[axis],b[axis]):
                    kind='reset' if e['driver'].startswith(('reset_','local_reset','bind_reset')) or e['driver']=='context_provider' else 'clock'
                    witnesses.append(dict(driver=e['driver'],sink=e['sink'],pin=e['pin'],kind=kind))
            counts=collections.Counter(w['kind'] for w in witnesses)
            out[f'{axis}:{line}']=dict(clock=counts['clock'],reset=counts['reset'],clock_reserved=64,reset_reserved=64,
                                      geometric_crossings_within_reservation=all(counts[k]<=64 for k in ('clock','reset')),witnesses=witnesses)
    return out


def generate():
    root=R.ROOT/OUT;root.mkdir(parents=True,exist_ok=True)
    if (root/'model-r1.json').exists() or (root/'model-r1.json.gz').exists():raise ValueError('preserve committed verdict; use additive successor')
    print('constructing regional topology',flush=True)
    b,old,rows,direct=construct()
    print('binding all90metadata to matched source-owned reset mirror',flush=True)
    matched_reset(b,old,rows,direct)
    print('checking all56683 reset intervals at SS/FF',flush=True)
    timing=N.price(b);g=b.g;cut=cuts(g)
    area=65983.07303971479+23.80914+1.44342+len(g['added_primitive_cells'])*.10206+480*.10206+6*.10206
    failures=sum(s['reset_failures'] for c in timing.values() for s in c['scenarios'])
    result=dict(schema='QWEN_REGIONAL_COLLECTOR_MATCHED_RESET_R1',status='NUMERIC_CONSTRUCTION_NOT_PHYSICAL_ADMISSION',
        source_map_admission=False,PnR=False,additional_maps=0,numerical_runs=0,
        selected_map_sha256=M.MAP_SHA,clock_sinks=102352,provider_clock_FFs=2,reset_sinks=56683,
        selected_slot_um=[357.696,1360.8],selected_corridor_um=96.768,cell_ceiling_um2=125000,
        SS_setup_uncertainty_ps=60,FF_hold_uncertainty_ps=25,period_ps=833.3333333333334,
        source_group_count=len(g['local_group_ledger']),regional_collector_count=len(g['regional_collector_roots']),
        collector_cut_checks=cut,reset_interval_checks=timing,reset_failures_summed_scenarios=failures,
        clock_buffers=g['clock_buffer_count'],reset_buffers=g['reset_mirror_buffer_count'],
        added_distribution_cells=len(g['added_primitive_cells']),complete_cell_area_um2=area,
        cell_area_fit=area<=125000,all90_metadata_reset_ports_redirected=True,
        reset_source='Actual priced twoDFFASR/twoINV streaming parent provider with finite source-owned output feed; no ideal reset seed.',
        source_root_input_arrivals_observed=False,
        release_protocol='Existing two-edge provider release once at startup; matched mirror includes all direct and90metadata reset sinks; source-owned launch waits until latest qualified release edge.',
        proposed_startup_edge=max(s['proposed_first_accept_edge_after_provider_edge0'] for c in timing.values() for s in c['scenarios']),
        legal_cell_sites_proven=False,full_meander_track_occupancy_proven=False,macro_pin_access_proven=False,
        parent_binary_init_admitted=False,Russell_service_policy_admitted=False,
        historical_models_preserved=[str(N.OUT/'model-r1.json'),str(N.B.OUT/'model-r1.json')])
    if failures:result['status']='FAIL_REGIONAL_RESET_INTERVAL'
    elif any(not r['geometric_crossings_within_reservation'] for r in cut.values()):result['status']='FAIL_REGIONAL_COLLECTOR_CUT'
    elif any(s['same_source_skew_ps']>20 for c in timing.values() for s in c['scenarios']):result['status']='FAIL_REGIONAL_CLOCK_SKEW'
    payload=gzip.compress(R.canon(g),mtime=0);(root/'allocation-r1.json.gz').write_bytes(payload)
    M.write(root/'model-r1.json',result)
    print(json.dumps({k:result[k] for k in ('status','clock_buffers','complete_cell_area_um2','reset_failures_summed_scenarios','proposed_startup_edge')},indent=2),flush=True)
    return result


if __name__=='__main__':generate()
