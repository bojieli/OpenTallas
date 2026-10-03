#!/usr/bin/env python3
"""Source-sized leaf-driver release/ACK allocation. Analytical only, default off.

An actual clock leaf with reset-bearing FFs defines one release group. Read-only
capture FFs do not acquire invented reset pins. No reset timing exceptions.
"""
import collections
import gzip
import hashlib
import json
import math
import functools
from pathlib import Path
import qwen_rom_native_collector_clock as A
H=A.V.H
R=A.R; M=A.M; N=A.N; G=A.G
OUT=Path('results/uarch/qwen_rom_native_local_release_20261002')
INV=H.INV
AND='AND3x1_ASAP7_75t_R'
C=.165790
ABSTRACTS=functools.lru_cache(maxsize=1)(A.abstracts)


def model_bytes(name):
    path=R.ROOT/OUT/name
    return path.read_bytes() if path.exists() else gzip.decompress(path.with_suffix('.json.gz').read_bytes())


def record(name):return json.loads(model_bytes(name))


def load():
    old,rows,direct=N.inventory()
    g=json.loads(gzip.decompress((R.ROOT/A.OUT/'clock-allocation-r1.json.gz').read_bytes()))
    macros={r['instance'] for r in rows if r['group'] in ('ROM_clock','KV_clock')}
    sites=A.Sites([p['origin_um']+[p['origin_um'][0]+p['size_um'][0],p['origin_um'][1]+p['size_um'][1]]
                   for n,p in g['cell_sites'].items() if n in macros])
    for n,p in g['cell_sites'].items():
        if 'pin_CLK_rect_M4_um' in p:continue
        x,y=p['origin_um'];sites.rows[round(y/.270)].append((round(x/.054),round((x+p['size_um'][0])/.054)))
    b=A.Builder(old,rows,sites,g['cell_sites']);b.g=g
    b.counter=1000000;b.bit=1+max(v for c in g['added_primitive_cells'].values() for vs in c['connections'].values() for v in vs if isinstance(v,int))
    return b,old,rows,direct


def place(b,name,typ,pos):
    p=b.sites.put(pos,ABSTRACTS()[typ]['size_um'][0],G.region(pos))
    b.placements[name]=p;b.g['nominal_node_coordinates_um'][name]=[p['origin_um'][0]+p['size_um'][0]/2,p['origin_um'][1]+.135]
    return name


def construct(correct_phase=False):
    b,old,rows,direct=load();g=b.g;coords=g['nominal_node_coordinates_um']
    clkedges=list(g['wire_edges']);incoming={e['sink']:e for e in clkedges};targets=set(direct)|set(g['metadata_reset_sinks'])
    leaves=collections.defaultdict(list)
    for e in clkedges:
        if e['sink'] in targets:leaves[e['driver']].append(e['sink'])
    assert sum(map(len,leaves.values()))==56683
    # One assertion tree mirrors the actual ancestor collectors, not a second
    #global equalization chain. Each local group owns just its direct RST pins.
    ancestors=set()
    for leaf in leaves:
        n=leaf
        while n in incoming:
            ancestors.add(n);n=incoming[n]['driver']
        ancestors.add(n)
    mirrors={n:b.buf(coords[n],'native_assert') for n in sorted(ancestors)}
    for e in clkedges:
        if e['driver'] in ancestors and e['sink'] in ancestors:b.edge(mirrors[e['driver']],mirrors[e['sink']],'A',e['length_um'])
    groups=[];physical=[];ack_nodes={};ack_edges=[]
    for i,(leaf,sinks) in enumerate(sorted(leaves.items())):
        pos=coords[leaf];ffs=[];invs=[]
        for stage in range(2):
            ff=place(b,f'native_release_{i}.ff{stage}',R.ASR,pos);ffs.append(ff)
            inv=place(b,f'native_release_{i}.inv{stage}',INV,coords[ff]);invs.append(inv)
            physical.extend([dict(instance=ff,type=R.ASR),dict(instance=inv,type=INV)])
            b.net['cells'][ff]=dict(type=R.ASR,connections=dict(D=['ONE' if stage==0 else invs[0]],SETN=['ONE']))
            b.edge(leaf,ff,'CLK',2);b.edge(mirrors[leaf],ff,'RESETN',2)
            g['source_clock_sinks'].append(dict(instance=ff,cell=R.ASR,pin='CLK',group='native_local_release_clock'))
        hold=b.buf(coords[invs[0]],'native_release_hold');second=b.buf(coords[ffs[1]],'native_release_hold')
        g['added_primitive_cells'][hold]['connections']['A']=[invs[0]]
        b.edge(hold,second,'A',16);b.edge(second,ffs[1],'D',16)
        entry=b.buf(coords[invs[1]],'native_release_reset')
        g['added_primitive_cells'][entry]['connections']['A']=[invs[1]]
        # Minimum characterized load is real paid wire, never extrapolation.
        lengths=[sum(abs(a-c) for a,c in zip(coords[entry],coords[n])) for n in sinks]
        pin=sum(M.pin_cap(b.net['cells'][n]['type'],'RESETN','ss') for n in sinks)
        extra=max(0,(2.90-pin)/C-sum(lengths))/len(sinks)
        for n,length in zip(sinks,lengths):b.edge(entry,n,'RESETN',length+extra)
        q=dict(group=i,root=leaf,region=list(G.region(pos)),FFs=ffs,inversions=invs,
               hold_entry=hold,reset_entry=entry,reset_targets=sinks,assert_driver=mirrors[leaf])
        ack=b.buf(coords[invs[1]],'native_ACK_input')
        q['ACK_entry']=ack
        ack_nodes[invs[1]]=dict(type=INV,region=q['region'])
        ack_nodes[ack]=dict(type=R.BUF,region=q['region'])
        ack_edges.append(dict(driver=invs[1],sink=ack,pin='A',length_um=max(2,sum(abs(a-c) for a,c in zip(coords[invs[1]],coords[ack])))))
        groups.append(q)
    # Source-owned startup ACK: regional AND reduction, then one root reduction.
    #No ready subset or layer/token replication. All gates/landing sites paid.
    regional=collections.defaultdict(list)
    for q in groups:regional[tuple(q['region'])].append(q['ACK_entry'])
    def reduce(nodes,label):
        nodes=sorted(nodes,key=lambda n:N.B.morton(coords[n]))
        depth=0
        while len(nodes)>1:
            parents=[]
            for j in range(0,len(nodes),3):
                children=nodes[j:j+3];pos=[sum(coords[n][d] for n in children)/len(children) for d in (0,1)]
                name=place(b,f'{label}_{depth}_{j}',AND,pos);physical.append(dict(instance=name,type=AND));ack_nodes[name]=dict(type=AND,region=list(G.region(pos)))
                for pin,n in zip(('A','B','C'),children):
                    length=max(2,sum(abs(a-c) for a,c in zip(coords[n],coords[name])))
                    ack_edges.append(dict(driver=n,sink=name,pin=pin,length_um=length))
                parents.append(name)
            nodes=parents;depth+=1
        return nodes[0],depth
    regional_roots=[];regional_depths={}
    for reg,nodes in sorted(regional.items()):
        root,depth=reduce(nodes,f'native_ACK_{reg[0]}_{reg[1]}');regional_roots.append(root);regional_depths[str(reg)]=depth
    ackroot,depth=reduce(regional_roots,'native_ACK_root')
    # ACK receiver is a real 2-FF synchronization/registered launch demand.
    #Its domain phase/epoch exports must be supplied by the parent source.
    receiver=[]
    if correct_phase:
        receiver_leaf=min(leaves,key=lambda n:sum(abs(a-c) for a,c in zip(coords[n],coords['context_provider'])))
    else:receiver_leaf=g['root_driver']
    for stage in range(2):
        ff=place(b,f'native_ACK_receiver.ff{stage}',R.ASR,coords[receiver_leaf]);receiver.append(ff)
        inv=place(b,f'native_ACK_receiver.inv{stage}',INV,coords[ff]);physical.extend([dict(instance=ff,type=R.ASR),dict(instance=inv,type=INV)])
        b.net['cells'][ff]=dict(type=R.ASR,connections={})
        b.edge(receiver_leaf,ff,'CLK',2);b.edge(mirrors[receiver_leaf],ff,'RESETN',2)
        g['source_clock_sinks'].append(dict(instance=ff,cell=R.ASR,pin='CLK',group='startup_ACK_clock'))
    ack_edges.append(dict(driver=ackroot,sink=receiver[0],pin='D',length_um=max(2,sum(abs(a-c) for a,c in zip(coords[ackroot],coords[receiver[0]])))))
    source=b.buf(coords['context_provider'],'native_assert_source');g['wire_edges'].append(dict(driver='context_provider',sink=source,pin='A',length_um=16))
    target=mirrors[g['root_driver']];distance=max(16,sum(abs(a-c) for a,c in zip(coords[source],coords[target])));count=math.ceil(distance/128);prev=source
    for k in range(1,count):
        n=b.buf([coords[source][d]+(coords[target][d]-coords[source][d])*k/count for d in (0,1)],'native_assert_source');b.edge(prev,n,'A',distance/count);prev=n
    b.edge(prev,target,'A',distance/count)
    if correct_phase:
        prior=record('model-r1.json')['timing']['ss']['raw_reset_checks']
        low=min(q['interval_ps'][0] for q in prior);high=max(q['interval_ps'][1] for q in prior)
        cycle=math.ceil(high/H.PERIOD)
        window=[cycle*H.PERIOD+50.049297-low,cycle*H.PERIOD+791.5025333333334-high]
        if window[0]>window[1]:raise ValueError('no common source-owned assertion phase window')
        # A single constraint-derived finite source-feed chain, not an option
        #sweep or copied global clock equalization network.
        cap=16*C+R.library('ss')[2][(R.BUF,'A')]['cap_fF']
        minstage=R.envelope(R.library('ss')[1][R.BUF],'cell_rise',cap,5,80)[0]
        stages=math.ceil(sum(window)/2/minstage)
        edge=next(e for e in g['wire_edges'] if e['sink']==source)
        g['wire_edges'].remove(edge);previous=None
        for k in range(stages):
            n=b.buf(coords[source],'native_assert_phase')
            if previous:b.edge(previous,n,'A',16)
            else:g['wire_edges'].append(dict(driver='context_provider',sink=n,pin='A',length_um=edge['length_um']))
            previous=n
        b.edge(previous,source,'A',16)
        g['assert_phase_construction']=dict(required_extra_SS_delay_window_ps=window,
            cycle=cycle,derived_stages=stages,minimum_characterized_stage_delay_ps=minstage,
            wire_per_stage_um=16,ACK_receiver_clock_leaf=receiver_leaf)
    assert_edges=collections.defaultdict(list)
    for e in g['wire_edges']:
        if e['driver'].startswith('native_assert'):assert_edges[e['driver']].append(e)
    for driver,edges in assert_edges.items():
        pins=min(sum(M.pin_cap((g['added_primitive_cells'].get(e['sink']) or b.net['cells'][e['sink']])['type'],e['pin'],corner) for e in edges) for corner in ('ss','ff'))
        extra=max(0,(2.90-pins)/C-sum(e['length_um'] for e in edges))/len(edges)
        for e in edges:e['length_um']+=extra
    g.update(local_release_groups=groups,release_physical_cells=physical,ACK_nodes=ack_nodes,ACK_edges=ack_edges,
             ACK_regional_roots=regional_roots,ACK_root=ackroot,ACK_receiver_FFs=receiver,ACK_regional_depths=regional_depths,ACK_root_depth=depth)
    return b


def checks(b):
    g=b.g;result={};outgoing=collections.defaultdict(list)
    for e in g['wire_edges']:outgoing[e['driver']].append(e)
    joins=R.obj(R.OUT/'inputs/launch_join_cells_r1.json')
    ackout=collections.defaultdict(list)
    for e in g['ACK_edges']:ackout[e['driver']].append(e)
    for corner in ('ss','ff'):
        _,libs,caps=R.library(corner);ck,_,loads=M.propagate(g,b.net,corner,{g['root_driver']:{t:[0,0,5,80] for t in ('rise','fall')}})
        source=ck['context_provider:clk_stream']['rise'];provider=R.price()['provider_LUT_envelopes'][corner]
        cap=sum(e['length_um']*C+caps[(R.BUF,'A')]['cap_fF'] for e in outgoing['context_provider'])+joins[corner]['pin_caps_fF']['C']+32*C
        pad=R.envelope(libs[R.BUF],'cell_rise',cap);old=R.envelope(libs[R.BUF],'cell_rise',provider['last_pad_cap_bound_fF']);rel=[provider['release_before_distribution_minmax_ps'][i]+pad[i]-old[i] for i in (0,1)]
        slew=R.envelope(libs[R.BUF],'rise_transition',cap)
        raw,_,rawloads=M.propagate(g,b.net,corner,{'context_provider':{t:[source[0]+rel[0],source[1]+rel[1],*slew] for t in ('rise','fall')}})
        seeds={};rawchecks=[];releases=[]
        for q in g['local_release_groups']:
            for ff in q['FFs']:rawchecks.append(dict(instance=ff,**H.phase(ck[ff+':CLK']['rise'],raw[ff+':RESETN']['rise'])))
            clk=ck[q['FFs'][1]+':CLK']['rise'];rr=raw[q['FFs'][1]+':RESETN']['rise'];edge=math.ceil((rr[1]-clk[0])/H.PERIOD)+1
            inv=q['inversions'][1];f=q['FFs'][1];coords=g['nominal_node_coordinates_um']
            qcap=caps[(INV,'A')]['cap_fF']+C*max(2,sum(abs(a-c) for a,c in zip(coords[f],coords[inv])))
            delay=R.envelope(libs[R.ASR],'cell_fall',qcap,*clk[2:],related='CLK');qs=R.envelope(libs[R.ASR],'fall_transition',qcap,*clk[2:],related='CLK')
            load=caps[(R.BUF,'A')]['cap_fF']+C*max(2,sum(abs(a-c) for a,c in zip(coords[inv],coords[q['reset_entry']])))
            load+=sum(e['length_um']*C+caps[(R.BUF,'A')]['cap_fF'] for e in ackout[inv])
            d=R.envelope(libs[INV],'cell_rise',load,*qs);sl=R.envelope(libs[INV],'rise_transition',load,*qs)
            wave=[clk[0]+edge*H.PERIOD+delay[0]+d[0],clk[1]+edge*H.PERIOD+delay[1]+d[1],*sl]
            seeds[q['reset_entry']]={t:wave[:] for t in ('rise','fall')};releases.append(dict(group=q['group'],clean_edge=edge,INV_output_load_fF=load,release_wave=wave))
        for ff in g['ACK_receiver_FFs']:
            rawchecks.append(dict(instance=ff,**H.phase(ck[ff+':CLK']['rise'],raw[ff+':RESETN']['rise'])))
        rst,_,rloads=M.propagate(g,b.net,corner,seeds);controlled=[]
        for q in g['local_release_groups']:
            for n in q['reset_targets']:controlled.append(dict(instance=n,**H.phase(ck[n+':CLK']['rise'],rst[n+':RESETN']['rise'])))
        nominal=[]
        for input_slew in (5,80):
            states,_,_=M.propagate(g,b.net,corner,{g['root_driver']:{t:[0,0,input_slew,input_slew] for t in ('rise','fall')}})
            waves=[states[r['instance']+':'+r['pin']]['rise'] for r in g['source_clock_sinks']]
            nominal.append(dict(root_slew_ps=input_slew,skew_ps=max(w[1] for w in waves)-min(w[0] for w in waves)))
        result[corner]=dict(raw_reset_checks=rawchecks,controlled_reset_checks=controlled,local_release_waves=releases,
            raw_reset_failures=sum(q['fail'] for q in rawchecks),controlled_reset_failures=sum(q['fail'] for q in controlled),
            nominal_same_source_clock_scenarios=nominal,max_clock_load_fF=max(loads.values()),max_assert_load_fF=max(rawloads.values()),max_local_reset_load_fF=max(rloads.values()))
    return result


def generate(revision=1):
    root=R.ROOT/OUT;root.mkdir(parents=True,exist_ok=True)
    modelname=f'model-r{revision}.json';allocationname=f'allocation-r{revision}.json.gz'
    if (root/modelname).exists() or (root/modelname).with_suffix('.json.gz').exists():raise ValueError('preserve verdict')
    b=construct(correct_phase=revision==2);g=b.g
    print('actual leaf/reset groups',len(g['local_release_groups']),flush=True)
    # Publish incremental allocation before costly analytical propagation.
    (root/allocationname).write_bytes(gzip.compress(R.canon(g),mtime=0))
    timing=checks(b);n=len(g['local_release_groups']);types=collections.Counter(p['type'] for p in g['release_physical_cells'])
    area=65983.07303971479+23.80914+1.44342+len(g['added_primitive_cells'])*.10206+types[R.ASR]*.37908+types[INV]*.04374+types[AND]*.08748+486*.10206
    cuts={}
    ACK_ids={id(e) for e in g['ACK_edges']}
    for axis,bounds in enumerate(G.BOUNDS):
        for line in bounds[1:-1]:
            counts=collections.Counter()
            for e in g['wire_edges']+g['ACK_edges']:
                a=g['nominal_node_coordinates_um'][e['driver']][axis];c=g['nominal_node_coordinates_um'][e['sink']][axis]
                if min(a,c)<line<=max(a,c):counts['reset_ACK' if id(e) in ACK_ids or e['driver'].startswith(('native_assert','native_release')) or e['driver']=='context_provider' else 'clock']+=1
            cuts[f'{axis}:{line}']=dict(clock=counts['clock'],reset_ACK=counts['reset_ACK'],reservation_each=64)
    report=dict(schema='QWEN_NATIVE_LEAF_RELEASE_ACK_R1',selected_map_sha256=M.MAP_SHA,source_clock_pins=102352,source_reset_pins=56683,
        actual_reset_clock_leaf_groups=n,new_local_FFs=2*n,startup_ACK_receiver_FFs=2,total_clock_pins=102352+2*n+2,
        total_reset_pins=56683+2*n+2,provider_two_FFs_separate=True,physical_cell_types=dict(types),
        buffer_cells=len(g['added_primitive_cells']),complete_reserved_cell_area_um2=area,ceiling_um2=125000,corridor_um=96.768,
        field1536_cell_area_mm2=area*1536/1e6,field_original_macro_area_mm2=129.67316324352,
        timing=timing,cuts=cuts,PG_ledger_sha256=R.sha(M.OUT/'directional-PG-allocation-r1.json'),
        assertion_phase_construction=g.get('assert_phase_construction'),
        startup_ACK='Every reset-bearing leaf; regional AND then one parent ACK receiver. Current source-owned request/epoch only; reset clears ACK, inhibits launch; interrupted accepted owner requires abort/quarantine.',
        steady_extra_cycles=0,startup_clean_edges_by_group=True,
        contextual_accepted_demand='Held binary instruction/address and current KV readiness snapshot must survive until ACK and measured producer setup/hold windows; benchmark start pulse is not a physical launch contract.',
        unqualified=['clock_skew','ACK_gate_load_slew_and_return_route','FF0_FF1_internal_setup_hold','ACK_receiver_CDC_phase','root_external_assert_feed_and_pulse','cell_pin_landing_vias','full_meander_route_occupancy','1536_field_standard_cell_orientation','parent_binary_init_and_epoch_abort_exports'],
        source_map_admission=False,contextual_SSFF=False,PnR=False,additional_maps=0,numerical_runs=0,default_enabled=False,
        status='FAIL_UNQUALIFIED_NATIVE_RELEASE_CONTEXT',historical_387_410_and_49_77_failures_preserved=True)
    M.write(root/modelname,report)
    print(json.dumps({k:report[k] for k in ('actual_reset_clock_leaf_groups','total_clock_pins','total_reset_pins','complete_reserved_cell_area_um2','cuts')},indent=2),flush=True)
    print({c:(v['raw_reset_failures'],v['controlled_reset_failures'],v['nominal_same_source_clock_scenarios']) for c,v in timing.items()},flush=True)


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--revision',type=int,choices=(1,2),default=1)
    generate(p.parse_args().revision)
