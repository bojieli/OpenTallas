#!/usr/bin/env python3
"""Bind actual mapped sink allocation to finite root feeds and a directional PG plan.
This is an additive analytical construction, never synthesis, P&R or decode.
The selected failed-map survival verdict remains binding.
"""
import argparse
import collections
import gzip
import hashlib
import json
import math
import re
from pathlib import Path
import qwen_rom_current_reset_construction as R

ROOT=R.ROOT
OUT=Path('results/uarch/qwen_rom_mapped_root_pg_context_20261002')
MAP_SHA='92b6cf36af938f89468c6ce07d7bd5624239172eecd914de3eb750ff435802a0'


def load(path):return json.loads((ROOT/path).read_text())
def digest(path):return hashlib.sha256((ROOT/path).read_bytes()).hexdigest()
def write(path,data):path.write_text(json.dumps(data,sort_keys=True,indent=2)+'\n')


def tech():
    text=(ROOT/OUT/'inputs/tech.lef').read_text()
    tracks=(ROOT/OUT/'inputs/make_tracks.tcl').read_text()
    out={}
    for name in ('M4','M5','M6','M7','M8'):
        body=re.search(r'^LAYER '+name+r'\n(.*?)^END '+name+r'$',text,re.M|re.S)[1]
        direction=re.search(r'DIRECTION\s+(\w+)',body)[1]
        row=re.search(r'make_tracks '+name+r' -x_offset (\S+) -x_pitch (\S+) -y_offset (\S+) -y_pitch (\S+)',tracks)
        axis='x' if direction=='VERTICAL' else 'y'
        out[name]=dict(direction=direction,axis=axis,width=float(re.search(r'\bWIDTH\s+([\d.]+)',body)[1]),
            pitch=float(row[2 if axis=='x' else 4]),offset=float(row[1 if axis=='x' else 3]),
            # Wide-wire spacing table dominates nominal small-width SPACING.
            PG_clearance=.072 if name in ('M5','M6') else .04)
    return out


def centers(lo,hi,pitch,offset):
    first=math.ceil((lo-offset)/pitch-1e-8)
    return [round(offset+i*pitch,9) for i in range(first,math.ceil((hi-offset)/pitch-1e-8))]


def stripes(layers,slot):
    # Snap the installed strategy to actual track centers; no off-grid phases.
    rows=[]
    for layer,width,phase,ground_delta in [('M5',.12,.300,.192),('M6',.288,.528,.384)]:
        limit=slot['w_um'] if layers[layer]['axis']=='x' else slot['h_um']
        for net,offset in [('VDD',phase),('VSS',phase+ground_delta)]:
            for center in centers(0,limit,5.376,offset):
                if center-width/2<0 or center+width/2>limit:continue
                rows.append(dict(layer=layer,net=net,center_um=center,width_um=width,
                    extent_um=[0,slot['h_um'] if layer=='M5' else slot['w_um']],
                    legal_track_axis=layers[layer]['axis']))
    return rows


def corridor_pg():
    selected=load(R.OUT/'inputs/model.json');slot=selected['slot'];layers=tech()
    corridor=selected['corridor']['width_um'];center=slot['w_um']/2
    bands={'M5':[center-corridor/2,center+corridor/2],
           'M7':[center-corridor/2,center+corridor/2],
           'M6':[393.12,393.12+corridor],'M8':[393.12,393.12+corridor]}
    pg=stripes(layers,slot);free={};stats={}
    for layer,band in bands.items():
        spec=layers[layer];raw=centers(*band,spec['pitch'],spec['offset'])
        blocked=[x for x in raw if any(s['layer']==layer and abs(x-s['center_um'])<s['width_um']/2+spec['width']/2+spec['PG_clearance']-1e-9 for s in pg)]
        usable=[x for x in raw if x not in set(blocked)]
        budget=math.floor(len(raw)*.5)
        if len(usable)<budget:raise ValueError('explicit PG consumes more than reserved half '+layer)
        # The other half includes PG exclusions; never subtract PG twice.
        free[layer]=usable[:budget]
        stats[layer]=dict(**spec,band_um=band,raw_tracks=len(raw),PG_excluded_tracks=len(blocked),
                         half_share_signal_budget=budget,signal_centers_um=free[layer])
    # Preserve selected756M6+604M8 counts. Pair each collector with its required
    # vertical feed; extra M5/M7 capacity is not added to selected capacity.
    lanes=[]
    for vertical,horizontal,count,via in [('M5','M6',756,'VIA56'),('M7','M8',604,'VIA78')]:
        if min(len(free[vertical]),len(free[horizontal]))<count:raise ValueError('paired directional capacity fails selected model')
        for i in range(count):
            index=len(lanes);kind='fill' if index<1048 else 'clock' if index<1112 else 'reset' if index<1176 else 'spare'
            lanes.append(dict(index=index,kind=kind,vertical_layer=vertical,horizontal_layer=horizontal,
                vertical_x_um=free[vertical][i],horizontal_y_um=free[horizontal][i],turn_via=via,
                vertical_extent_um=[0,slot['h_um']],horizontal_extent_um=[0,slot['w_um']]))
    # Connect same-polarity PG intersections with explicit vias; finite geometry.
    via56=[dict(net=v['net'],via='VIA56',x_um=v['center_um'],y_um=h['center_um'])
           for v in pg if v['layer']=='M5' for h in pg if h['layer']=='M6' and v['net']==h['net']]
    return dict(schema='QWEN_DIRECTIONAL_PG_CORRIDOR_V1',selected_slot=slot,selected_corridor_um=corridor,
        layers=stats,PG_stripes=pg,PG_same_polarity_vias=via56,signal_lanes=lanes,
        selected_M6_M8_capacity_not_increased=True,vertical_M5_M7_feed_required=True,
        PG_pitch_um=5.376,template_pitch_um=5.4,
        PG_snap_reason='Installed5.4pitch/phase do not align every stripe to right-way tracks.5.376 is112M5 or84M6 pitches.',
        horizontal_collector_band_is_explicit=True,signal_capacity=1360,fill=1048,clock=64,reset=64,spare=184,
        global_signal_turns=1360,macro_M4_pin_access_and_OBS='Macro terminal aprons require separate pin-access geometry; no blanket via across OBS.',
        PG_geometry_allocated=True,IR_EM_DRC_routed=False,physical_admission=False)


def root_bind(net,allocation):
    """Add root input feeds and all old metadata-reset wires to exact r1 edits."""
    import copy
    cells=copy.deepcopy(allocation['added_primitive_cells']);coords={n:tuple(v) for n,v in allocation['nominal_node_coordinates_um'].items()}
    original=net['cells'];edits=copy.deepcopy(allocation['original_cell_pin_edits'])
    edges=copy.deepcopy(allocation['wire_edges']);ports=net['ports'];clk=ports['clk_stream']['bits'][0];rst=ports['reset_stream_n']['bits'][0]
    def con(name):
        if name in cells:return cells[name]['connections']
        return {**original[name]['connections'],**edits.get(name,{})}
    maxbit=max(b for row in cells.values() for bits in row['connections'].values() for b in bits if isinstance(b,int))
    def fresh():
        nonlocal maxbit
        maxbit+=1;return maxbit
    def setpin(name,pin,bit):
        if name in cells:cells[name]['connections'][pin]=[bit]
        else:edits.setdefault(name,{})[pin]=[bit]
    added=[]
    def buf(name,inputbit,pos):
        output=fresh();cells[name]=dict(type=R.BUF,connections=dict(A=[inputbit],Y=[output]));coords[name]=pos;added.append(name);return output
    def route(driver,outbit,target,pin,length=None):
        start=coords[driver];end=coords[target]
        length=max(16,abs(end[0]-start[0])+abs(end[1]-start[1])) if length is None else length
        parts=math.ceil(length/128);previous=driver;bit=outbit
        for k in range(1,parts):
            name='bind_'+driver+'_'+target.replace('.','_')+'_'+pin+'_seg'+str(k)
            bit=buf(name,bit,tuple(start[d]+(end[d]-start[d])*k/parts for d in (0,1)))
            edges.append(dict(driver=previous,sink=name,pin='A',length_um=length/parts));previous=name
        setpin(target,pin,bit);edges.append(dict(driver=previous,sink=target,pin=pin,length_um=length/parts))
    center=coords['context_provider'];entry=(center[0],393.12)
    # One physical clock entry, one global hub,5isolated finite branches:
    #4current tree roots and the2FFprovider's CLK pin (aggregate module load).
    clock_targets=[(name,'A') for name,c in cells.items() if c['type']==R.BUF and con(name).get('A')==[clk]]
    if len(clock_targets)!=4:raise ValueError('exact4mapped clock tree roots required')
    clock_targets.append(('context_provider','clk_stream'))
    portbit=buf('bind_clock_entry',clk,entry)
    hubbit=buf('bind_clock_hub',portbit,center)
    route('bind_clock_entry',portbit,'bind_clock_hub','A')
    for i,(target,pin) in enumerate(clock_targets):
        name='bind_clock_branch'+str(i);bit=buf(name,hubbit,center)
        edges.append(dict(driver='bind_clock_hub',sink=name,pin='A',length_um=16))
        route(name,bit,target,pin)
    # Reset also gets a real entry route into the two provider RESETN pins.
    bit=buf('bind_reset_entry',rst,entry);route('bind_reset_entry',bit,'context_provider','external_reset_n')
    # Construct all original15 metadata-reset BUF wires. Identify them by
    #actual RESETN connectivity, independent of optimized source wire names.
    bufdrivers={c['connections']['Y'][0]:name for name,c in original.items() if c['type']==R.BUF}
    descendants=collections.defaultdict(list);legacy=set();metadata=[]
    for name,c in original.items():
        if c['type']!=R.ASR or c['connections']['RESETN']==[rst]:continue
        metadata.append(name);bit=c['connections']['RESETN'][0];seen=set()
        while bit in bufdrivers:
            driver=bufdrivers[bit]
            if driver in seen:raise ValueError('legacy reset cycle')
            seen.add(driver);legacy.add(driver);descendants[driver].append(name);bit=original[driver]['connections']['A'][0]
        if bit!=rst:raise ValueError('unbound actual metadata reset producer')
    if len(legacy)!=15 or len(metadata)!=37:raise ValueError('actual legacy15BUF/37FF join failed')
    # Keep r1 allocated root coordinates; derive interior anchors from actual
    #descendant FFs. Original reset leaf input/output identities are preserved.
    for n in sorted(legacy):
        if n not in coords:coords[n]=tuple(sum(coords[t][d] for t in descendants[n])/len(descendants[n]) for d in (0,1))
    targets=collections.defaultdict(list)
    for n in sorted(legacy):
        b=original[n]['connections']['A'][0]
        if b in bufdrivers and bufdrivers[b] in legacy:targets[bufdrivers[b]].append((n,'A'))
    for n in metadata:targets[bufdrivers[original[n]['connections']['RESETN'][0]]].append((n,'RESETN'))
    for driver,rows in sorted(targets.items()):
        output=original[driver]['connections']['Y'][0]
        for i,(target,pin) in enumerate(rows):
            name='bind_legacy_'+driver.replace('.','_')+'_branch'+str(i);bit=buf(name,output,coords[driver])
            edges.append(dict(driver=driver,sink=name,pin='A',length_um=16));route(name,bit,target,pin)
    # The actual raw reset also controls one combinational pin. R1 did not
    #include it in the FF census. Release it through the same finite provider.
    controls=[]
    for name,c in original.items():
        for pin,bits in c['connections'].items():
            if bits==[rst] and c['type']!=R.ASR and not(c['type']==R.BUF and name in legacy):controls.append((name,pin))
    if sorted(original[n]['type'] for n,p in controls)!=['NAND2xp33_ASAP7_75t_R','NAND3xp33_ASAP7_75t_R']:raise ValueError('different raw-reset control fanout')
    release=con('context_provider')['released_reset_n'][0]
    hub=buf('bind_reset_control_hub',release,center)
    edges.append(dict(driver='context_provider',sink='bind_reset_control_hub',pin='A',length_um=16))
    for i,(name,pin) in enumerate(controls):
        coords[name]=(center[0]+32,center[1]+i*16)
        driver='bind_reset_control_branch'+str(i);bit=buf(driver,hub,center)
        edges.append(dict(driver='bind_reset_control_hub',sink=driver,pin='A',length_um=16));route(driver,bit,name,pin)
    return dict(added_primitive_cells=cells,original_cell_pin_edits=edits,wire_edges=edges,
        nominal_node_coordinates_um=coords,new_source_binding_buffers=added,legacy_reset_BUFFERS=sorted(legacy),
        reset_combinational_controls=[dict(instance=n,pin=p,cell=original[n]['type']) for n,p in controls],
        entry_ports=dict(clock=clk,reset=rst),complete_gate_PASS=False)


def control_caps():
    return load(OUT/'inputs/reset-control-liberty.json')


def pin_cap(kind,pin,corner):
    if kind=='ot_qwen_rom_reset_parent_provider':
        ff=R.library(corner)[2]
        if pin=='clk_stream':return 2*ff[(R.ASR,'CLK')]['cap_fF']
        if pin=='external_reset_n':return 2*ff[(R.ASR,'RESETN')]['cap_fF']
        raise ValueError('unpriced provider sink '+pin)
    if kind in ('NAND2xp33_ASAP7_75t_R','NAND3xp33_ASAP7_75t_R'):return control_caps()[corner][kind]['pin_caps_fF'][pin]
    return R.library(corner)[2][(kind,pin)]['cap_fF']


def propagate(graph,net,corner,seeds):
    """Bound rise/fall arrival and slew on every finite BUF wire; no zero RC."""
    cells={**net['cells'],**graph['added_primitive_cells']};outgoing=collections.defaultdict(list)
    for e in graph['wire_edges']:outgoing[e['driver']].append(e)
    raw,libs,caps=R.library(corner);buf=libs[R.BUF]
    rc=R.price()['nominal_RC'];coef=rc['signal_cap_fF_per_um'];res=rc['signal_resistance_ohm_per_um']
    states=dict(seeds);pending=list(seeds);loads={};output={}
    # State at each pin: rise/fall [arrivalmin,arrivalmax,slewmin,slewmax].
    while pending:
        driver=pending.pop();arcs=outgoing[driver]
        if not arcs:continue
        load=sum(e['length_um']*coef+pin_cap(cells[e['sink']]['type'],e['pin'],corner) for e in arcs)
        loads[driver]=load
        if not 2.88<=load<=46.08:raise ValueError('load outside admitted BUF characterization '+driver)
        if driver=='context_provider':wave=states[driver] # source FF/pads separately characterized
        else:
            wave={}
            for transition in ('rise','fall'):
                lo,hi,slo,shi=states[driver][transition]
                delay=R.envelope(buf,'cell_'+transition,load,slo,shi)
                slew=R.envelope(buf,transition+'_transition',load,slo,shi)
                wave[transition]=[lo+delay[0],hi+delay[1],slew[0],slew[1]]
            if max(w[3] for w in wave.values())>320:raise ValueError('buffer slew exceeds unchanged320ps bound')
        output[driver]=wave
        for e in arcs:
            sink=e['sink'];pin=e['pin'];length=e['length_um']
            elmore=res*length*(coef*length/2+pin_cap(cells[sink]['type'],pin,corner))/1000
            state={t:[w[0]+elmore,w[1]+elmore,w[2],w[3]] for t,w in wave.items()}
            states[sink+':'+pin]=state
            if cells[sink]['type']==R.BUF and pin=='A':
                if sink in states:raise ValueError('multiply driven finite buffer')
                states[sink]=state;pending.append(sink)
    return states,output,loads


def timing(graph,net):
    result={};provider=R.price()['provider_LUT_envelopes'];sinkrows=json.loads(gzip.decompress((ROOT/R.OUT/'mapped-sink-census-r1.json.gz').read_bytes()))
    clocknames=[r for r in sinkrows if r['group'] in ('logic_clock','ROM_clock','KV_clock')]
    rawrst=net['ports']['reset_stream_n']['bits'][0]
    for corner in ('ss','ff'):
        clock_states,clock_outputs,clockloads=propagate(graph,net,corner,{'bind_clock_entry':{t:[0,0,5,80] for t in ('rise','fall')}})
        root=clock_states['context_provider:clk_stream']
        if max(w[3] for w in root.values())>80:raise ValueError('root source violates declared80ps clock slew')
        # Price changed release fanout: 3BUF branches + actual launch C input,
        #16um/branch plus32um local join wire=80um total route.
        lib=R.library(corner);cap=3*lib[2][(R.BUF,'A')]['cap_fF']+load(R.OUT/'inputs/launch_join_cells_r1.json')[corner]['pin_caps_fF']['C']+.165790*80
        pad=R.envelope(lib[1][R.BUF],'cell_rise',cap)
        oldpad=R.envelope(lib[1][R.BUF],'cell_rise',provider[corner]['last_pad_cap_bound_fF'])
        release_bounds=[provider[corner]['release_before_distribution_minmax_ps'][i]+pad[i]-oldpad[i] for i in (0,1)]
        release_slew=R.envelope(lib[1][R.BUF],'rise_transition',cap)
        # RESET deassert rise only. Fall propagation is tracked independently
        #for reset source pulse-width pricing, not treated as release polarity.
        release={t:[root['rise'][0]+release_bounds[0],root['rise'][1]+release_bounds[1],*release_slew] for t in ('rise','fall')}
        reset_states,reset_outputs,resetloads=propagate(graph,net,corner,{'context_provider':release})
        ext_states,ext_outputs,extloads=propagate(graph,net,corner,{'bind_reset_entry':{t:[0,0,5,80] for t in ('rise','fall')}})
        local=ext_states['context_provider:external_reset_n']
        required_ext_min=100+root['rise'][1]-local['rise'][0]
        required_ext_max=780+root['rise'][0]-local['rise'][1]
        pulse_loss=max(local['fall'][1]-local['rise'][0],local['rise'][1]-local['fall'][0])
        endpoint=[]
        for name,c in net['cells'].items():
            if c['type']!=R.ASR:continue
            ck=clock_states[name+':CLK']['rise'];rr=reset_states[name+':RESETN']['rise']
            phase=[rr[0]-ck[1],rr[1]-ck[0]]
            endpoint.append(dict(instance=name,group='direct' if c['connections']['RESETN']==[rawrst] else 'metadata',
                reset_phase_minmax_ps=phase,removal_bound_margin_ps=phase[0]-50.049297,
                recovery_bound_margin_ps=791.5025333333334-phase[1]))
        clocks=[clock_states[r['instance']+':'+r['pin']]['rise'] for r in clocknames]
        result[corner]=dict(clock_sinks=len(clocks),reset_FF_sinks=len(endpoint),
            clock_arrival_minmax_ps=[min(c[0] for c in clocks),max(c[1] for c in clocks)],
            provider_CLK_arrival_minmax_ps=root['rise'][:2],provider_CLK_slew_minmax_ps=root['rise'][2:],
            provider_external_reset_route_rise_minmax_ps=local['rise'][:2],
            external_reset_required_deassert_minmax_ps=[required_ext_min,required_ext_max],
            external_reset_min_pulse_ps=330+max(0,pulse_loss),
            release_relative_provider_clock_minmax_ps=release_bounds,
            branch_max_load_fF=max([*clockloads.values(),*resetloads.values(),*extloads.values()]),
            removal_worst=min(endpoint,key=lambda e:e['removal_bound_margin_ps']),
            recovery_worst=min(endpoint,key=lambda e:e['recovery_bound_margin_ps']),
            reset_bound_failures=sum(e['removal_bound_margin_ps']<0 or e['recovery_bound_margin_ps']<0 for e in endpoint),
            analytical_nominal_RC_only=True,actual_extracted_contextual_SSFF=False,
            scope='Complete actual FF clock/reset feed propagation. No arithmetic data setup/hold, macro capture timing, P&R or gate PASS credit.')
    return result


def main():
    p=argparse.ArgumentParser();p.add_argument('--work',type=Path,default=R.LIVE);p.add_argument('--out',type=Path,default=ROOT/OUT);args=p.parse_args()
    args.out.mkdir(parents=True,exist_ok=True)
    if (args.out/'model-r1.json').exists():raise ValueError('refuse overwrite modeled verdict')
    if hashlib.sha256((args.work/'mapped.json').read_bytes()).hexdigest()!=MAP_SHA:raise ValueError('different selected map')
    net=json.loads((args.work/'mapped.json').read_text())['modules']['ot_qwen_rom_fulltile_tp4_context_top']
    allocation=json.loads(gzip.decompress((ROOT/R.OUT/'asbuilt-finite-allocation-r1.json.gz').read_bytes()))
    graph=root_bind(net,allocation);pg=corridor_pg()
    blob=gzip.compress(R.canon(graph),mtime=0);(args.out/'root-bound-allocation-r1.json.gz').write_bytes(blob)
    write(args.out/'directional-PG-allocation-r1.json',pg)
    # Actual loads only. Source preopt budgets are never priced as mapped pins.
    price=load(R.OUT/'mapped-loads-r1.json');count=len(graph['new_source_binding_buffers'])
    report=timing(graph,net)
    area=count*.10206
    retained=load(OUT/'inputs/retained-source-model-handoff.json')
    if retained['source_sha256']!=digest(OUT/'inputs/retained-r3.sv'):raise ValueError('r3retained source mismatch')
    retained_price=dict(required_explicit_FFs=85,old_actual_FFs=32,added_FFs=53,
        added_FF_area_um2=53*.37908,restoring_INV_reservation=85,restoring_INV_area_um2=85*.04374,
        total_retention_increment_um2=53*.37908+85*.04374,
        mapped_counts_after_retention=dict(clock=102299+53,reset=56630+53),
        nominal_pin_loads_after_retention={c:{'clock_fF':sum(v[c+'_cap_fF'] for g,v in price['groups'].items() if g in ('logic_clock','ROM_clock','KV_clock'))+53*R.library(c)[2][(R.ASR,'CLK')]['cap_fF'],
        'reset_fF':sum(v[c+'_cap_fF'] for g,v in price['groups'].items() if g in ('direct_parent_reset','distributed_reset'))+53*R.library(c)[2][(R.ASR,'RESETN')]['cap_fF'],
        '85restoring_INV_QN_load_fF':85*R.library(c)[2][('INVx1_ASAP7_75t_R','A')]['cap_fF']} for c in ('ss','ff')},
        Z_literal_contract_failure_retained=True,source_contract_qualified=False,
        finite_distribution_scope='Existing actual102299clock/56630reset plus53required control FFs; actual source handoff pinned, restorationINV never assumed free.',
        source=retained,source_map_admission=False)
    record=dict(schema='QWEN_ACTUAL_MAPPED_ROOT_PG_CONTEXT_V1',source_commit='752fffd8a7dd31742f383ca59b89598db51d7222',mapped_sha256=MAP_SHA,
        Euclid_committed_join=load(OUT/'inputs/origins.json'),mapped_loads=price,
        selected_slot=pg['selected_slot'],selected_corridor_um=96.768,
        source_binding=dict(new_buffers=count,additional_area_um2=area,root_clock_branches=5,
            old_metadata_reset_buffers_bound=len(graph['legacy_reset_BUFFERS']),
            raw_reset_combinational_controls=graph['reset_combinational_controls'],
            input_clock_driver='bind_clock_entry',input_reset_driver='bind_reset_entry',wire_RC_is_finite=True),
        retention_successor_price=retained_price,
        nominal_area_with_retention_inverters_and_source_binding_um2=load(R.OUT/'asbuilt-finite-allocation-receipt-r1.json')['nominal_area_after_preservation53_um2']+85*.04374+area,
        final53_distribution_and_full_data_wire_area_unmeasured=True,
        timing_preflight=report,PG_binding=dict(signal_lanes=1360,turn_vias=1360,PG_stripes=len(pg['PG_stripes']),PG_vias=len(pg['PG_same_polarity_vias']),
            vertical_feeds='M5/M7',horizontal_collectors='M6/M8',half_signal_share_preserved=True),
        startup=dict(provider_release_edges=2,first_accept_edge3_requires_all_endpoint_constraints=True,
            additional_steady_cycles=0,latency_credit=False),
        root_allocation_sha256=hashlib.sha256(blob).hexdigest(),
        graph_gate=load(OUT/'inputs/euclid-portable-replay.json')['survival'],
        admission=dict(complete_gate_PASS=False,contextual_SSFF=False,PnR=False,hardware_adoption=False,
            numerical_runs=0,additional_maps=0,installed_CTS_precondition=False),
        next_gate='Preserve80mask/5bank source replicas and finish semantic graph joins; source/PG allocation is now finite. Qualify setup/hold and macro timing only after graph admission.')
    write(args.out/'model-r1.json',record)
    sources=[Path(__file__).relative_to(ROOT),Path('tests/test_qwen_rom_mapped_root_pg_context.py'),Path('tools/uarch_model_qwen_mapped_context.py')]
    sources += [x.relative_to(ROOT) for x in (ROOT/OUT/'inputs').iterdir() if x.is_file()]
    sources += [R.OUT/n for n in ('model-r1.json','mapped-loads-r1.json','mapped-sink-census-r1.json.gz','asbuilt-finite-allocation-r1.json.gz')]
    sources += [Path('tools/qwen_rom_current_reset_construction.py'),R.PROVIDER]
    sources += [R.RESET/'inputs'/('seq_'+c+'.lib.gz') for c in ('ss','ff')]+[R.RESET/'inputs'/('invbuf_'+c+'.lib.gz') for c in ('ss','ff')]
    for macro in ('ot_rom_4096x266_m8','ot_sram_1r1w_128x256_m1_r2c2'):
        sources += [Path('physical/asap7_memory_macros')/macro/(macro+s) for s in ('.lef','_ss.lib','_ff.lib')]
    write(args.out/'sourcepins-r1.json',dict(sha256={str(p):digest(p) for p in sources}))
    write(args.out/'artifact-sha256-r1.json',{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in args.out.iterdir() if p.is_file() and p.name!='artifact-sha256-r1.json'})
    print(json.dumps(dict(new_source_buffers=count,source_area_um2=area,timing={c:{k:r[k] for k in ('clock_sinks','reset_FF_sinks','reset_bound_failures','external_reset_required_deassert_minmax_ps')} for c,r in report.items()},complete_gate_PASS=False),indent=2))

if __name__=='__main__':main()
