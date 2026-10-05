#!/usr/bin/env python3
"""One source-sized local successor feed. Characterized load inversion only;
no parameter sweep, synthesis, decode simulation, or physical build.
"""
import collections
import copy
import gzip
import hashlib
import json
import math
import inspect
from pathlib import Path
import qwen_rom_balanced_successor_clock as B
R=B.R;M=B.M;S=B.S;L=B.L
OUT=Path('results/uarch/qwen_rom_local_subtree_context_20261002')
C=.165790


def inventory():
    old=json.loads(gzip.decompress((R.ROOT/S.OUT/'successor-allocation-r1.json.gz').read_bytes()))
    census=json.loads(gzip.decompress((R.ROOT/R.OUT/'mapped-sink-census-r1.json.gz').read_bytes()))
    removed=set(old['removed_old_control_FFs'])
    rows=[r for r in census if r['group'] in ('logic_clock','ROM_clock','KV_clock') and r['instance'] not in removed]
    rows += [dict(instance=r['instance'],pin='CLK',cell=R.ASR,group='successor_control_clock') for r in old['source_control_cells']]
    rows.append(dict(instance='context_provider',pin='clk_stream',cell='ot_qwen_rom_reset_parent_provider',group='provider2FF'))
    direct={r['instance'] for r in census if r['group']=='direct_parent_reset'}
    if len(rows)!=102353 or len(direct)!=56593:raise ValueError('different selected source')
    return old,rows,direct


class Builder:
    def __init__(self,old,rows):
        self.g=dict(added_primitive_cells={},original_cell_pin_edits={},wire_edges=[],nominal_node_coordinates_um={r['instance']:old['nominal_node_coordinates_um'][r['instance']] for r in rows})
        self.net=dict(cells={r['instance']:dict(type=r['cell'],connections={}) for r in rows})
        self.bit=1;self.counter=0
    def buf(self,pos,label='local'):
        n=label+'_'+str(self.counter);self.counter+=1
        self.g['added_primitive_cells'][n]=dict(type=R.BUF,connections=dict(A=['PENDING'],Y=[self.bit]));self.bit+=1
        self.g['nominal_node_coordinates_um'][n]=list(pos);return n
    def edge(self,a,b,p,length):
        cells=self.g['added_primitive_cells'];coords=self.g['nominal_node_coordinates_um']
        target=cells[b] if b in cells else self.net['cells'][b]
        target['connections'][p]=cells[a]['connections']['Y'][:]
        self.g['wire_edges'].append(dict(driver=a,sink=b,pin=p,length_um=length,
            meander_um=max(0,length-sum(abs(x-y) for x,y in zip(coords[a],coords[b])))))
    def tree(self,targets,label,minimum_levels=1):
        coords=self.g['nominal_node_coordinates_um'];level=0
        targets=sorted(targets,key=lambda r:B.morton(coords[r[0]]))
        while True:
            parents=[]
            for i in range(0,len(targets),8):
                children=targets[i:i+8];pos=[sum(coords[n][d] for n,p in children)/len(children) for d in (0,1)]
                parent=self.buf(pos,label)
                # Equalize only this eight-child local subtree's geometry.
                distance=max(16,max(sum(abs(x-y) for x,y in zip(pos,coords[n])) for n,p in children))
                count=math.ceil(distance/128);length=distance/count
                for j in range(8):
                    branch=self.buf(pos,label+'_isolate');self.edge(parent,branch,'A',16)
                    if j>=len(children):continue
                    n,p=children[j];previous=branch
                    for k in range(1,count):
                        seg=self.buf([pos[d]+(coords[n][d]-pos[d])*k/count for d in (0,1)],label+'_segment')
                        self.edge(previous,seg,'A',length);previous=seg
                    self.edge(previous,n,p,length)
                parents.append((parent,'A'))
            level+=1;targets=parents
            if len(parents)==1 and level>=minimum_levels:return parents[0][0],level


def construct(old,rows):
    builder=Builder(old,rows);coords=builder.g['nominal_node_coordinates_um'];groups=collections.defaultdict(list)
    for r in rows:
        x,y=coords[r['instance']]
        key=(int(x/(357.696/8)),int(y/(1360.8/32)),r['cell'])
        groups[key].append(r)
    roots={};ledger=[]
    for key,targets in sorted(groups.items()):
        # Separate actual pin types, including macros. No macro's high clock
        #capacitance is copied onto100k ordinary FF clocks.
        root,depth=builder.tree([(r['instance'],r['pin']) for r in targets],'local_leaf',4)
        roots[root]=targets;ledger.append(dict(root=root,bin=list(key),sinks=len(targets),levels=depth))
    collector,depth=builder.tree([(n,'A') for n in roots],'local_collector')
    pos=[178.848,393.12];entry=builder.buf(pos,'local_clock_entry');end=coords[collector]
    distance=max(16,sum(abs(x-y) for x,y in zip(pos,end)));count=math.ceil(distance/128);previous=entry
    for i in range(1,count):
        n=builder.buf([pos[d]+(end[d]-pos[d])*i/count for d in (0,1)],'local_clock_input_segment')
        builder.edge(previous,n,'A',distance/count);previous=n
    builder.edge(previous,collector,'A',distance/count)
    builder.g['added_primitive_cells'][entry]['connections']['A']=['PRIMARY_CLOCK_SOURCE']
    builder.g.update(root_driver=entry,source_clock_sinks=rows,local_group_ledger=ledger,
        collector_levels=depth,local_bin_um=[357.696/8,1360.8/32],global_equalization_chain_duplicated=False)
    return builder,roots


def inverse_balance(builder,roots):
    g=builder.g;net=builder.net
    states,_,loads=M.propagate(g,net,'ss',{g['root_driver']:{t:[0,0,5,5] for t in ('rise','fall')}})
    arrivals={n:max(states[r['instance']+':'+r['pin']]['rise'][1] for r in rs) for n,rs in roots.items()}
    target=max(arrivals.values())+100
    incoming={e['sink']:e for e in g['wire_edges']};lib=R.library('ss')[1][R.BUF];cap=R.library('ss')[2][(R.BUF,'A')]['cap_fF'];ledger=[]
    for root in roots:
        wave=states[root+':A']['rise'];delta=target-arrivals[root];oldroot=R.envelope(lib,'cell_rise',loads[root],wave[2],wave[3])[0]
        def evaluate(count,length):
            lo,hi,slo,shi=wave
            for i in range(count):
                load=cap+C*length
                delay=R.envelope(lib,'cell_rise',load,slo,shi);slew=R.envelope(lib,'rise_transition',load,slo,shi)
                elmore=.0265684*length*(C*length/2+cap)/1000
                lo+=delay[0]+elmore;hi+=delay[1]+elmore;slo,shi=slew
            return lo-wave[0]+R.envelope(lib,'cell_rise',loads[root],slo,shi)[0]-oldroot
        # Select the finite stage count from characterized capacity; invert
        #this single topology's load. This is not an architectural sweep.
        count=max(1,math.ceil(delta/120))
        while evaluate(count,128)<delta:count+=1
        while count>1 and evaluate(count,16)>delta:count-=1
        if evaluate(count,16)>delta:raise ValueError('fixed minimum local delay exceeds allocation')
        low,high=16.,128.
        for i in range(36):
            middle=(low+high)/2
            if evaluate(count,middle)<delta:low=middle
            else:high=middle
        length=(low+high)/2;edge=incoming[root];original_driver=edge['driver'];oldlength=edge['length_um']
        g['wire_edges'].remove(edge);first=None;previous=None
        for i in range(count):
            n=builder.buf(g['nominal_node_coordinates_um'][root],'local_balance')
            if previous:builder.edge(previous,n,'A',length)
            else:first=n;builder.edge(original_driver,n,'A',oldlength)
            previous=n
        builder.edge(previous,root,'A',length)
        ledger.append(dict(root=root,added_buffers=count,local_wire_per_stage_um=length,SS_requested_delay_ps=delta,
            SS_inverted_delay_ps=evaluate(count,length)))
    g['local_balance_ledger']=ledger;g['SS_balance_target_ps']=target


def reset_graph(builder,old,direct):
    g=builder.g;net=builder.net;clockcells=list(g['added_primitive_cells']);clockedges=list(g['wire_edges']);coords=g['nominal_node_coordinates_um']
    # One conservative reset mirror reservation. Dummy paths are paid; only
    #the56593actual direct RESETN endpoints receive reset. Metadata90keep
    #their exact original15BUFsource hierarchy and logicalleafownership.
    for name in clockcells:
        new='reset_'+name;g['added_primitive_cells'][new]=dict(type=R.BUF,connections=dict(A=['PENDING'],Y=[builder.bit]));builder.bit+=1;coords[new]=coords[name]
    for e in clockedges:
        if e['sink'] not in clockcells and e['sink'] not in direct:continue
        builder.edge('reset_'+e['driver'],'reset_'+e['sink'] if e['sink'] in clockcells else e['sink'], 'A' if e['sink'] in clockcells else 'RESETN',e['length_um'])
    # Keep source-owned metadata and both actual combinational reset controls.
    metadata=[r['instance'] for r in old['source_control_cells']]
    census=json.loads(gzip.decompress((R.ROOT/R.OUT/'mapped-sink-census-r1.json.gz').read_bytes()))
    metadata += [r['instance'] for r in census if r['group']=='distributed_reset' and r['instance'] not in old['removed_old_control_FFs']]
    incoming={(e['sink'],e['pin']):e for e in old['wire_edges']};kept={};pending=[(n,'RESETN') for n in metadata]
    pending += [(r['instance'],r['pin']) for r in old['reset_combinational_controls']]
    # Both physical root RESETN loads keep their finite external input feed.
    pending.append(('context_provider','external_reset_n'))
    while pending:
        n,p=pending.pop()
        if (n,p) not in incoming:continue # physical input entry is the seed
        e=incoming[n,p];kept[(n,p)]=e
        if e['driver']!='context_provider':pending.append((e['driver'],'A'))
    for e in kept.values():
        if e['driver'] not in coords:
            coords[e['driver']]=old['nominal_node_coordinates_um'][e['driver']]
            if e['driver'] in old['added_primitive_cells']:g['added_primitive_cells'][e['driver']]=copy.deepcopy(old['added_primitive_cells'][e['driver']])
            elif e['driver'] in old['legacy_reset_BUFFERS']:net['cells'][e['driver']]=dict(type=R.BUF,connections={})
            else:raise ValueError('unpriced retained reset driver '+e['driver'])
        n=e['sink']
        if n not in net['cells'] and n not in g['added_primitive_cells']:
            if n in old['added_primitive_cells']:g['added_primitive_cells'][n]=copy.deepcopy(old['added_primitive_cells'][n])
            else:net['cells'][n]=dict(type=R.BUF if n in old['legacy_reset_BUFFERS'] else next(r['cell'] for r in old['reset_combinational_controls'] if r['instance']==n),connections={})
            coords[n]=old['nominal_node_coordinates_um'][n]
        g['wire_edges'].append(copy.deepcopy(e))
    root='reset_'+g['root_driver'];pos=coords['context_provider'];end=coords[root]
    branch=builder.buf(pos,'local_reset_source');g['wire_edges'].append(dict(driver='context_provider',sink=branch,pin='A',length_um=16,meander_um=16))
    distance=max(16,sum(abs(x-y) for x,y in zip(pos,end)));count=math.ceil(distance/128);previous=branch
    for i in range(1,count):
        n=builder.buf([pos[d]+(end[d]-pos[d])*i/count for d in (0,1)],'local_reset_source_segment');builder.edge(previous,n,'A',distance/count);previous=n
    builder.edge(previous,root,'A',distance/count)
    g['reset_direct_sinks']=sorted(direct);g['metadata_reset_sinks']=metadata
    g['clock_buffer_count']=len(clockcells);g['reset_mirror_buffer_count']=len(clockcells)


def price(builder):
    g=builder.g;net=builder.net;result={};old=R.price();outgoing=collections.defaultdict(list)
    for e in g['wire_edges']:outgoing[e['driver']].append(e)
    for corner in ('ss','ff'):
        reports=[];libs=R.library(corner)
        cap=sum(e['length_um']*C+M.pin_cap((g['added_primitive_cells'].get(e['sink']) or net['cells'][e['sink']])['type'],e['pin'],corner) for e in outgoing['context_provider'])
        cap+=R.obj(R.OUT/'inputs/launch_join_cells_r1.json')[corner]['pin_caps_fF']['C']+32*C
        provider=old['provider_LUT_envelopes'][corner]
        pad=R.envelope(libs[1][R.BUF],'cell_rise',cap);oldpad=R.envelope(libs[1][R.BUF],'cell_rise',provider['last_pad_cap_bound_fF'])
        release=[provider['release_before_distribution_minmax_ps'][i]+pad[i]-oldpad[i] for i in (0,1)]
        slew=R.envelope(libs[1][R.BUF],'rise_transition',cap)
        for source_slew in (5,80):
            ck,_,cload=M.propagate(g,net,corner,{g['root_driver']:{t:[0,0,source_slew,source_slew] for t in ('rise','fall')}})
            source=ck['context_provider:clk_stream']['rise']
            rr,_,rload=M.propagate(g,net,corner,{'context_provider':{t:[source[0]+release[0],source[1]+release[1],*slew] for t in ('rise','fall')}})
            waves=[ck[r['instance']+':'+r['pin']]['rise'] for r in g['source_clock_sinks']]
            phases=[];period=833.3333333333334
            for name in g['reset_direct_sinks']+g['metadata_reset_sinks']:
                a=ck[name+':CLK']['rise'];b=rr[name+':RESETN']['rise'];raw=[b[0]-a[1],b[1]-a[0]]
                cycles=[math.floor(v/period) for v in raw];phase=[raw[i]-cycles[0]*period for i in (0,1)]
                phases.append(dict(instance=name,absolute_reset_minus_clock_ps=raw,release_cycle_offset=cycles,
                    phase_ps=phase,removal_margin_ps=phase[0]-50.049297,recovery_margin_ps=791.5025333333334-phase[1],
                    crosses_clock_edge=cycles[0]!=cycles[1]))
            reports.append(dict(primary_clock_slew_ps=source_slew,clock_arrival_minmax_ps=[min(w[0] for w in waves),max(w[1] for w in waves)],
                same_source_skew_ps=max(w[1] for w in waves)-min(w[0] for w in waves),provider_clock=source,
                root_clock_slew_pass=source[3]<=80,root_release_slew_ps=slew,root_release_slew_pass=slew[1]<=80,
                reset_FF_sinks=len(phases),reset_failures=sum(p['crosses_clock_edge'] or p['removal_margin_ps']<0 or p['recovery_margin_ps']<0 for p in phases),
                reset_removal_worst=min(phases,key=lambda p:p['removal_margin_ps']),reset_recovery_worst=min(phases,key=lambda p:p['recovery_margin_ps']),
                last_reset_edge_offset=max(p['release_cycle_offset'][1] for p in phases),
                proposed_first_accept_edge_after_provider_edge0=3+max(p['release_cycle_offset'][1] for p in phases),
                startup_not_admitted_if_any_reset_or_source_gate_fails=True,
                max_BUF_load_fF=max([*cload.values(),*rload.values()])))
        result[corner]=dict(scenarios=reports,release_relative_provider_clock_ps=release)
    return result


def main():
    out=R.ROOT/OUT;out.mkdir(parents=True,exist_ok=True)
    if (out/'model-r1.json').exists():raise ValueError('preserve failed verdict')
    old,rows,direct=inventory()
    checkpoint=out/'clock-construction-checkpoint-r1.json.gz'
    algorithm_hash=hashlib.sha256((''.join(inspect.getsource(f) for f in (Builder,construct,inverse_balance))+M.digest(S.OUT/'successor-allocation-r1.json.gz')+M.digest(Path('tools/qwen_rom_current_reset_construction.py'))+M.digest(Path('tools/qwen_rom_mapped_root_pg_context.py'))).encode()).hexdigest()
    if checkpoint.exists():
        saved=json.loads(gzip.decompress(checkpoint.read_bytes()))
        if saved['algorithm_sha256']!=algorithm_hash:raise ValueError('different clock constructor checkpoint')
        builder=Builder(old,rows);builder.g=saved['graph'];builder.net=saved['net'];roots=saved['roots']
        builder.bit=saved['bit'];builder.counter=saved['counter']
    else:
        builder,roots=construct(old,rows);inverse_balance(builder,roots)
        checkpoint.write_bytes(gzip.compress(R.canon(dict(graph=builder.g,net=builder.net,roots=roots,bit=builder.bit,counter=builder.counter,algorithm_sha256=algorithm_hash)),mtime=0))
    reset_graph(builder,old,direct)
    timing=price(builder);g=builder.g;coords=g['nominal_node_coordinates_um']
    cuts={}
    for axis,limits in ((0,(130.464,227.232)),(1,(393.12,489.888))):
        for line in limits:
            counts=collections.Counter('reset' if e['driver'].startswith('reset_') or e['driver'].startswith('local_reset') or not e['driver'].startswith('local_') else 'clock'
                for e in g['wire_edges'] if min(coords[e['driver']][axis],coords[e['sink']][axis])<line<=max(coords[e['driver']][axis],coords[e['sink']][axis]))
            cuts[f'{axis}:{line}']=dict(counts,clock_reserved=64,reset_reserved=64,all_meander_cut_proof=False)
    area=65983.07303971479+23.80914+1.44342+len(g['added_primitive_cells'])*.10206
    # Existing mapped15reset and76control buffers remain in65983subtotal.
    other=L.R.obj(L.OUT/'model-r1.json')
    extra_mask=480*.10206;launch_route=other['launch_route'];launch_area=launch_route['added_buffers']*.10206
    area+=extra_mask+launch_area
    macro_area=sum(R.C.macro_inventory(name,count)['total_area_um2'] for name,count in (('ot_rom_4096x266_m8',10),('ot_sram_1r1w_128x256_m1_r2c2',2)))
    result=dict(schema='QWEN_ONE_LOCAL_SUBTREE_CONTEXT_V1',status='CONSTRUCTION_COMPLETE_CONTEXT_NOT_ADMITTED',
        selected_map_sha256=M.MAP_SHA,retained_source_sha256=other['retained_source_sha256'],
        successor_clock_sinks=102352,provider_clock_FFs=2,successor_reset_sinks=56683,
        source_groups=len(roots),source_bins_um=g['local_bin_um'],clock_buffers=g['clock_buffer_count'],
        reset_mirror_buffers=g['reset_mirror_buffer_count'],added_distribution_cells=len(g['added_primitive_cells']),
        complete_cell_area_um2=area,cell_ceiling_um2=125000,cell_area_fit=area<=125000,
        area_terms_um2=dict(selected_mapped_cells=65983.07303971479,retention53FF85INV=23.80914,provider=1.44342,
            all_new_clock_reset_buffers=len(g['added_primitive_cells'])*.10206,mask_selector480BUF=extra_mask,launch_route=launch_area),
        selected_corridor_um=96.768,selected_slot_um=[357.696,1360.8],collector_cuts=cuts,
        tile_macro_area_um2=macro_area,tile_macro_plus_cells_area_um2=macro_area+area,tile_macro_plus_cells_area_fit=macro_area+area<=357.696*1360.8,
        timing=timing,clock_demand_ps=20,period_ps=833.3333333333334,SS_setup_uncertainty_ps=60,FF_hold_uncertainty_ps=25,
        steady_added_cycles=0,steady_latency_credit=False,startup_admitted=False,
        tilefield=dict(tiles=1536,slot_area_mm2=357.696*1360.8/1e6,complete_cell_area_mm2=area*1536/1e6,
            selected_field_area_mm2=357.696*1360.8*1536/1e6,die_other_area_mm2=67.347827,
            macro_area_mm2=macro_area*1536/1e6,macro_plus_cell_area_mm2=(macro_area+area)*1536/1e6,
            field_clock_ports=102352*1536,field_reset_pins=56683*1536,provider_extra_clock_FFs=2*1536,
            die_clock_reset_spine_and_other_domains_priced=False,field_capacity_not_full_die_signoff=True),
        persistent_KV=other['persistent_KV'],current_once_calendar=other['current_once_calendar'],
        PG=dict(source=str(M.OUT/'directional-PG-allocation-r1.json'),signal_capacity=1360,fill=1048,clock=64,reset=64,spare=184,
            macro_pin_via_access_proven=False,DRC_IR_EM=False,existing_stripes_preserved=True),
        binary_init_contract=other['driven_binary_initialization_contract'],source_reachable_binary_init_proof=False,
        source_map_admission=False,PnR=False,additional_maps=0,numerical_runs=0,
        launch='Actual source/provider arrival must be recomputed on this clock; prior632.65..999.82window not transferred',
        historical_global_lower_bound_um2=157385.58875971477,historical_global_fit=False,
        source_allocation_only=True,global_equalization_chain_duplicated=False,
        total_clock_reset_wire_um=sum(e['length_um'] for e in g['wire_edges']),
        total_meander_reservation_um=sum(e.get('meander_um',0) for e in g['wire_edges']))
    if not result['cell_area_fit']:result['status']='FAIL_LOCAL_SUBTREE_CELL_AREA'
    elif any(s['same_source_skew_ps']>20 for r in timing.values() for s in r['scenarios']):result['status']='FAIL_LOCAL_SUBTREE_CLOCK_SKEW'
    elif any(s['reset_failures'] for r in timing.values() for s in r['scenarios']):result['status']='FAIL_LOCAL_SUBTREE_RESET_PHASE'
    payload=gzip.compress(R.canon(g),mtime=0);(out/'local-subtree-allocation-r1.json.gz').write_bytes(payload)
    result['allocation_sha256']=hashlib.sha256(payload).hexdigest();M.write(out/'model-r1.json',result)
    paths=[Path(__file__).relative_to(R.ROOT),Path('tests/test_qwen_rom_local_subtree_context.py'),Path('tools/uarch_model_qwen_local_context.py'),S.OUT/'sourcepins-r1.json',L.OUT/'sourcepins-r1.json',B.OUT/'model-r1.json',M.OUT/'directional-PG-allocation-r1.json',R.OUT/'mapped-sink-census-r1.json.gz']
    M.write(out/'sourcepins-r1.json',dict(sha256={str(p):M.digest(p) for p in paths}))
    M.write(out/'artifact-sha256-r1.json',{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.iterdir() if p.is_file() and p.name!='artifact-sha256-r1.json'})
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
