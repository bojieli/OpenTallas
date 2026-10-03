#!/usr/bin/env python3
"""Actual-group local async-assert/two-FF-release construction and startup ACK.
Source allocation only; no timing exception for the raw reset synchronizer pins.
"""
import collections
import copy
import gzip
import json
import math
from pathlib import Path
import qwen_rom_regional_collector_context as G
R=G.R;M=G.M;N=G.N
OUT=Path('results/uarch/qwen_rom_local_release_context_20261002')
INV='INVx1_ASAP7_75t_R'
PERIOD=833.3333333333334


def load_clock():
    old,rows,direct=N.inventory()
    saved=json.loads(gzip.decompress((R.ROOT/G.OUT/'allocation-r1.json.gz').read_bytes()))
    b=N.Builder(old,rows);b.g=saved
    drop={n for n in saved['added_primitive_cells'] if n.startswith(('reset_','local_reset','bind_reset'))}
    saved['added_primitive_cells']={n:c for n,c in saved['added_primitive_cells'].items() if n not in drop}
    saved['wire_edges']=[e for e in saved['wire_edges'] if e['driver'] not in drop and e['sink'] not in drop and e['driver']!='context_provider']
    b.bit=1+max(x for c in saved['added_primitive_cells'].values() for vs in c['connections'].values() for x in vs if isinstance(x,int))
    b.counter=len(saved['added_primitive_cells'])+1000000
    outgoing=collections.defaultdict(list)
    for e in saved['wire_edges']:outgoing[e['driver']].append(e)
    sinks={r['instance']:r for r in rows};groups=[]
    for row in saved['local_group_ledger']:
        pending=[row['root']];nodes=set();targets=[]
        while pending:
            n=pending.pop()
            if n in nodes:continue
            nodes.add(n)
            for e in outgoing[n]:
                if e['sink'] in sinks:targets.append(e)
                else:pending.append(e['sink'])
        groups.append(dict(root=row['root'],region=row['region'],nodes=nodes,
                           reset_targets=[e for e in targets if e['sink'] in direct or e['sink'] in saved['metadata_reset_sinks']]))
    return b,old,rows,direct,groups


def construct():
    b,old,rows,direct,groups=load_clock();g=b.g;coords=g['nominal_node_coordinates_um']
    # Only the ancestor collector is mirrored for assertion. Local release
    #owns the downstream reset tree. No global clock-padding chain is copied.
    incoming={e['sink']:e for e in g['wire_edges']};clockedges=copy.deepcopy(g['wire_edges']);ancestor=set()
    for group in groups:
        n=group['root']
        while n in incoming:
            e=incoming[n];ancestor.add(n);ancestor.add(e['driver']);n=e['driver']
    for n in ancestor:
        name='assert_'+n;g['added_primitive_cells'][name]=dict(type=R.BUF,connections=dict(A=['PENDING'],Y=[b.bit]));b.bit+=1;coords[name]=coords[n]
    for e in clockedges:
        if e['driver'] in ancestor and e['sink'] in ancestor:
            b.edge('assert_'+e['driver'],'assert_'+e['sink'],'A',e['length_um'])
    metadata=set(g['metadata_reset_sinks']);release_rows=[]
    for index,group in enumerate(groups):
        root=group['root'];pos=coords[root];ffs=[]
        for stage in range(2):
            name=f'local_release_{index}.ff{stage}';ffs.append(name)
            b.net['cells'][name]=dict(type=R.ASR,connections=dict(D=['ONE' if stage==0 else f'local_release_{index}.q0'],SETN=['ONE']))
            coords[name]=[pos[0]+(-.54 if stage==0 else .54),pos[1]]
        clk=b.buf(pos,'local_release_clock')
        b.edge(root,clk,'A',16)
        for name in ffs:
            b.edge(clk,name,'CLK',16);b.edge('assert_'+root,name,'RESETN',16)
        # Two restoring INV cells have explicit output loads in price();
        #ACK and reset each receive a distinct isolated BUFx4 branch.
        entry=b.buf(pos,'local_release_reset_entry');ack=b.buf(pos,'local_release_ACK_entry')
        g['added_primitive_cells'][entry]['connections']['A']=[f'local_release_{index}.q1']
        g['added_primitive_cells'][ack]['connections']['A']=[f'local_release_{index}.q1']
        nodes=set()
        required={e['sink'] for e in group['reset_targets']}
        for name in list(required):
            n=name
            while n in incoming and n!=root:
                e=incoming[n];nodes.add(e['driver']);n=e['driver']
        nodes.discard(root)
        for n in nodes:
            name='local_RST_'+n;g['added_primitive_cells'][name]=dict(type=R.BUF,connections=dict(A=['PENDING'],Y=[b.bit]));b.bit+=1;coords[name]=coords[n]
        for e in clockedges:
            if e['driver'] not in nodes|{root}:continue
            if e['sink'] not in nodes and e['sink'] not in required:continue
            a=entry if e['driver']==root else 'local_RST_'+e['driver']
            target='local_RST_'+e['sink'] if e['sink'] in nodes else e['sink']
            b.edge(a,target,'A' if e['sink'] in nodes else 'RESETN',e['length_um'])
        release_rows.append(dict(group=index,root=root,region=group['region'],FFs=ffs,
            clock_branch=clk,assert_driver='assert_'+root,reset_entry=entry,ACK_entry=ack,
            reset_targets=sorted(required),restoring_inversions=2))
    # Source-owned root provider drives the finite assertion collector.
    first='assert_'+g['root_driver'];pos=coords['context_provider'];target=coords[first]
    source=b.buf(pos,'local_assert_source');g['wire_edges'].append(dict(driver='context_provider',sink=source,pin='A',length_um=16))
    distance=max(16,sum(abs(x-y) for x,y in zip(pos,target)));count=math.ceil(distance/128);previous=source
    for i in range(1,count):
        node=b.buf([pos[d]+(target[d]-pos[d])*i/count for d in (0,1)],'local_assert_source_segment');b.edge(previous,node,'A',distance/count);previous=node
    b.edge(previous,first,'A',distance/count)
    g['local_release_groups']=release_rows
    return b,old,rows,direct,groups


def phase(a,b):
    raw=[b[0]-a[1],b[1]-a[0]];cycles=[math.floor(v/PERIOD) for v in raw]
    values=[v-cycles[0]*PERIOD for v in raw]
    return dict(interval_ps=raw,phase_ps=values,cycles=cycles,removal_margin_ps=values[0]-50.049297,
                recovery_margin_ps=791.5025333333334-values[1],fail=cycles[0]!=cycles[1] or values[0]<50.049297 or values[1]>791.5025333333334)


def price(b):
    g=b.g;net=b.net;outgoing=collections.defaultdict(list)
    for e in g['wire_edges']:outgoing[e['driver']].append(e)
    result={}
    for corner in ('ss','ff'):
        _,lib,caps=R.library(corner);ff=lib[R.ASR];inv=lib[INV]
        ck,cout,loads=M.propagate(g,net,corner,{g['root_driver']:{t:[0,0,5,80] for t in ('rise','fall')}})
        source=ck['context_provider:clk_stream']['rise'];provider=R.price()['provider_LUT_envelopes'][corner]
        cap=sum(16*.165790+caps[(R.BUF,'A')]['cap_fF'] for e in outgoing['context_provider'])
        cap+=R.obj(R.OUT/'inputs/launch_join_cells_r1.json')[corner]['pin_caps_fF']['C']+32*.165790
        pad=R.envelope(lib[R.BUF],'cell_rise',cap);oldpad=R.envelope(lib[R.BUF],'cell_rise',provider['last_pad_cap_bound_fF'])
        rel=[provider['release_before_distribution_minmax_ps'][i]+pad[i]-oldpad[i] for i in (0,1)]
        slew=R.envelope(lib[R.BUF],'rise_transition',cap)
        raw,_,_=M.propagate(g,net,corner,{'context_provider':{t:[source[0]+rel[0],source[1]+rel[1],*slew] for t in ('rise','fall')}})
        seeds={};reports=[]
        for group in g['local_release_groups']:
            clk=ck[group['FFs'][1]+':CLK']['rise'];reset=raw[group['FFs'][1]+':RESETN']['rise']
            checks=[phase(ck[n+':CLK']['rise'],raw[n+':RESETN']['rise']) for n in group['FFs']]
            # Wait for observed release and two local edges. These cycles are
            #clean-transfer demands; ACK, not a fixed timer, qualifies launch.
            edge=math.ceil((reset[1]-clk[0])/PERIOD)+1
            qcap=caps[(INV,'A')]['cap_fF']+2*.165790
            q=R.envelope(ff,'cell_fall',qcap,*clk[2:],related='CLK')
            qs=R.envelope(ff,'fall_transition',qcap,*clk[2:],related='CLK')
            load=2*caps[(R.BUF,'A')]['cap_fF']+32*.165790
            delay=R.envelope(inv,'cell_rise',load,*qs);sl=R.envelope(inv,'rise_transition',load,*qs)
            wave=[clk[0]+edge*PERIOD+q[0]+delay[0],clk[1]+edge*PERIOD+q[1]+delay[1],*sl]
            if group['reset_targets']:seeds[group['reset_entry']]={t:wave[:] for t in ('rise','fall')}
            reports.append(dict(group=group['group'],raw_reset_FF_checks=checks,local_second_edge=edge,
                ACK_before_isolation_buffer_wave=wave,controlled_sinks=len(group['reset_targets'])))
        rst,_,rloads=M.propagate(g,net,corner,seeds)
        checks=[]
        for group in g['local_release_groups']:
            for name in group['reset_targets']:
                checks.append(dict(instance=name,group=group['group'],**phase(ck[name+':CLK']['rise'],rst[name+':RESETN']['rise'])))
        waves=[ck[r['instance']+':'+r['pin']]['rise'] for r in g['source_clock_sinks']]
        result[corner]=dict(groups=reports,controlled_endpoint_checks=checks,
            controlled_reset_failures=sum(v['fail'] for v in checks),
            raw_local_FF_reset_failures=sum(c['fail'] for r in reports for c in r['raw_reset_FF_checks']),
            source_endpoint_clock_skew_ps=max(w[1] for w in waves)-min(w[0] for w in waves),
            source_root_slew_ps=source[2:],root_release_slew_ps=slew,
            max_CLK_BUF_load_fF=max(loads.values()),max_RST_BUF_load_fF=max(rloads.values()),
            source_release_interval_ps=rel,local_release_pulse_lower_bound_demand_ps=330+PERIOD,
            pulse_transfer_and_internal_stage_setup_hold_qualified=False)
    return result


def generate():
    root=R.ROOT/OUT;root.mkdir(parents=True,exist_ok=True)
    if (root/'model-r1.json').exists() or (root/'model-r1.json.gz').exists():raise ValueError('preserve verdict')
    print('construct actual311group local release and regional assertion',flush=True)
    b,old,rows,direct,groups=construct()
    print('check raw622FF reset intervals and56683 controlled sink intervals',flush=True)
    timing=price(b);count=len(groups)
    # ACK reduction is reduced in each actual region before crossing cuts.
    regions=collections.Counter(tuple(g['region']) for g in groups)
    ack_gates=sum(sum(R.tree_count(n,3)['levels_leaf_to_root']) for n in regions.values())+R.tree_count(len(regions),3)['buffers']
    area=65983.07303971479+23.80914+1.44342+len(b.g['added_primitive_cells'])*.10206+count*2*(.37908+.04374)+ack_gates*.08748+480*.10206+6*.10206
    result=dict(schema='QWEN_ACTUAL_GROUP_LOCAL_RELEASE_R1',status='CONSTRUCTED_NOT_ADMITTED',
        groups=count,local_FFs=2*count,restoring_INV=2*count,added_local_clock_pins=2*count,
        added_local_raw_reset_pins=2*count,baseline_successor_clock_pins=102352,baseline_successor_reset_pins=56683,
        total_source_clock_pins=102352+2*count,provider_FFs_separate=2,
        ACK_region_groups={str(k):v for k,v in regions.items()},ACK_AND3_gate_reservation=ack_gates,
        ACK_return_crossing_demand_per_cut=len(regions),ACK_routes_and_sink_load_price_complete=False,
        complete_reserved_cell_area_um2=area,cell_ceiling_um2=125000,
        selected_map_sha256=M.MAP_SHA,selected_corridor_um=96.768,
        timing=timing,SS_setup_uncertainty_ps=60,FF_hold_uncertainty_ps=25,
        source_owned_epoch_abort='ACK valid only for current held request identity. Reset inhibits launch, clears both local FFs and ready state; accepted owners need explicit abort/quarantine. No wrap or silent epoch reuse while debt survives.',
        reset_release_observed_ACK_required=True,startup_once_not_per_layer_token=True,
        steady_added_cycles=0,PnR=False,source_map_admission=False,additional_maps=0,numerical_runs=0,
        legal_cell_sites_proven=False,full_track_occupancy_proven=False)
    if any(r['controlled_reset_failures'] or r['raw_local_FF_reset_failures'] for r in timing.values()):result['status']='FAIL_LOCAL_RELEASE_RESET_INTERVAL'
    M.write(root/'model-r1.json',result)
    (root/'allocation-r1.json.gz').write_bytes(gzip.compress(R.canon(b.g),mtime=0))
    print(json.dumps({k:result[k] for k in ('status','groups','local_FFs','complete_reserved_cell_area_um2')},indent=2),flush=True)
    print({c:(r['controlled_reset_failures'],r['raw_local_FF_reset_failures'],r['source_endpoint_clock_skew_ps']) for c,r in timing.items()},flush=True)


if __name__=='__main__':generate()
