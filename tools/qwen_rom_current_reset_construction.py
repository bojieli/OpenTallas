#!/usr/bin/env python3
"""Construct source-matched reset/clock context around the ONE existing fullmap.
No synthesis invocation. Existing mapped bytes stay immutable. Exact finite
buffer graph emitted after the live map completes, with declared RC/slew bounds.
"""
import argparse,collections,functools,gzip,hashlib,importlib.util,json,math,re
from pathlib import Path
import qwen_rom_physical_context_contract as C

ROOT=C.ROOT
OUT=Path('results/uarch/qwen_rom_current_reset_construction_20261002')
RESET=C.RESET
LIVE=Path('/tmp/qwen-fulltile-source-map-smin6-r1-20261002')
PROVIDER=Path('rtl/physical/ot_qwen_rom_reset_parent_provider.sv')
BUF='BUFx4_ASAP7_75t_R'
ASR='DFFASRHQNx1_ASAP7_75t_R'


def read(path):return C.read(path)
def obj(path):return C.object_at(path)
def sha(path):return hashlib.sha256((ROOT/path).read_bytes()).hexdigest()
def canon(value):return json.dumps(value,sort_keys=True,separators=(',',':')).encode()


@functools.lru_cache(maxsize=128)
def tables(cell,kind,related=None):
    bodies=[cell]
    if related:
        bodies=[C.block(cell,m.start()) for m in re.finditer(r'\btiming\s*\(',cell)]
        bodies=[b for b in bodies if re.search(r'related_pin\s*:\s*"'+related+'"',b)]
    out=[]
    for body in bodies:
        for m in re.finditer(r'\b'+kind+r'\s*\(',body):
            t=C.block(body,m.start());x,y=[[float(v) for v in s.split(',')] for s in re.findall(r'index_[12]\s*\("([^"]+)"\)',t)]
            rows=[[float(v) for v in row.split(',')] for row in re.findall(r'"([\d., eE+-]+)"',t.split('values',1)[1])]
            if len(rows)!=len(x) or any(len(r)!=len(y) for r in rows):raise ValueError('invalid LUT shape')
            out.append((x,y,rows))
    if not out:raise ValueError('missing characterized '+kind)
    return out


def interpolate(table,slew,cap):
    x,y,z=table
    if not x[0]<=slew<=x[-1] or not y[0]<=cap<=y[-1]:raise ValueError('no LUT extrapolation')
    def bracket(a,v):
        i=next((i for i in range(len(a)-1) if a[i]<=v<=a[i+1]),len(a)-2)
        return i,(v-a[i])/(a[i+1]-a[i])
    i,u=bracket(x,slew);j,v=bracket(y,cap)
    return (1-u)*((1-v)*z[i][j]+v*z[i][j+1])+u*((1-v)*z[i+1][j]+v*z[i+1][j+1])


def envelope(cell,kind,cap,slew_min=5,slew_max=80,related=None):
    values=[]
    for t in tables(cell,kind,related):
        values += [interpolate(t,s,cap) for s in set([slew_min,slew_max]+[s for s in t[0] if slew_min<=s<=slew_max])]
    return min(values),max(values)


@functools.lru_cache(maxsize=2)
def library(corner):
    raw=read(RESET/('inputs/seq_'+corner+'.lib.gz'))+read(RESET/('inputs/invbuf_'+corner+'.lib.gz'))
    for name in ('ot_rom_4096x266_m8','ot_sram_1r1w_128x256_m1_r2c2'):
        raw+=read(Path('physical/asap7_memory_macros')/name/(name+'_'+corner+'.lib'))
    cells={m[1]:C.block(raw,m.start()) for m in re.finditer(r'\bcell\s*\(([^)]+)\)',raw)}
    return raw,cells,C.pin_caps(raw)


def tree_count(sinks,fanout=8):
    levels=[]
    while sinks>1:
        sinks=math.ceil(sinks/fanout);levels.append(sinks)
    return dict(levels_leaf_to_root=levels,buffers=sum(levels),depth=len(levels))


def price():
    selected=obj(OUT/'inputs/model.json');inventory=obj(OUT/'inputs/current_source_inventory.json')
    pins=obj(OUT/'inputs/sourcepins.json')
    if pins['commit']!='752fffd8a7dd31742f383ca59b89598db51d7222' or selected['corridor']['width_um']!=96.768:raise ValueError('wrong live map/model')
    clock=inventory['current_SMIN6_clock_bits_preopt'];reset=inventory['current_SMIN6_async_reset_bits_preopt']
    rc=read(OUT/'inputs/setRC.tcl')
    wirecap=float(re.search(r'set_wire_rc -signal.*?-capacitance ([\d.Ee+-]+)',rc)[1])
    wireres=float(re.search(r'set_wire_rc -signal -resistance ([\d.Ee+-]+)',rc)[1])
    timing={};area={}
    joins=obj(OUT/'inputs/launch_join_cells_r1.json')
    launch_sink=obj(OUT/'inputs/launch-sink-r1.json')['sinks']
    if len(launch_sink)!=1 or launch_sink[0]['cell']!=ASR or launch_sink[0]['pin']!='D':raise ValueError('different actual launch sink')
    for corner in ('ss','ff'):
        raw,cells,caps=library(corner)
        for name in (ASR,'INVx1_ASAP7_75t_R',BUF):area[name]=float(re.search(r'\barea\s*:\s*([\d.]+)',cells[name])[1])
        invcap=caps[('INVx1_ASAP7_75t_R','A')]['cap_fF']+wirecap*1
        invout=caps[(BUF,'A')]['cap_fF']+wirecap*2
        stage1_invout=caps[(ASR,'D')]['cap_fF']+wirecap*2
        padcap=caps[(BUF,'A')]['cap_fF']+wirecap*32
        q=envelope(cells[ASR],'cell_fall',invcap,related='CLK')
        stage1_inv=envelope(cells['INVx1_ASAP7_75t_R'],'cell_rise',stage1_invout)
        inv=envelope(cells['INVx1_ASAP7_75t_R'],'cell_rise',invout)
        pad=envelope(cells[BUF],'cell_rise',padcap)
        slew=envelope(cells[BUF],'rise_transition',padcap)
        # Last pad drives two reset-tree roots and the actual launch-join C pin.
        lastcap=2*caps[(BUF,'A')]['cap_fF']+joins[corner]['pin_caps_fF']['C']+wirecap*64
        last=envelope(cells[BUF],'cell_rise',lastcap)
        lastslew=envelope(cells[BUF],'rise_transition',lastcap)
        joincap=caps[(BUF,'A')]['cap_fF']+wirecap*2
        launch_driver_cap=caps[(ASR,'D')]['cap_fF']+wirecap*32
        launch_driver_delay=envelope(cells[BUF],'cell_rise',launch_driver_cap)
        launch_driver_slew=envelope(cells[BUF],'rise_transition',launch_driver_cap)
        join_delay=envelope(joins[corner]['cell_definition'],'cell_rise',joincap)
        join_slew=envelope(joins[corner]['cell_definition'],'rise_transition',joincap)
        if join_slew[1]>80:raise ValueError('launch join violates chosen slew bound')
        timing[corner]=dict(root_QN_wire1um_cap_fF=invcap,root_INV_wire2um_cap_fF=invout,
            stage1_INV_to_stage2_D_wire2um_cap_fF=stage1_invout,stage1_INV_rise_minmax_ps=stage1_inv,
            root_external_reset_pin_cap_fF=2*caps[(ASR,'RESETN')]['cap_fF'],
            launch_join_wire2um_cap_fF=joincap,launch_join_rise_minmax_ps=join_delay,
            launch_driver_wire32um_cap_fF=launch_driver_cap,launch_driver_rise_minmax_ps=launch_driver_delay,
            launch_driver_slew_minmax_ps=launch_driver_slew,
            launch_join_slew_minmax_ps=join_slew,
            launch_arrival_from_external_go_ready_minmax_ps=[50+join_delay[0]+launch_driver_delay[0],650+join_delay[1]+launch_driver_delay[1]],
            root_clock_pin_cap_fF=2*caps[(ASR,'CLK')]['cap_fF'],
            reset_pad_wire32um_cap_fF=padcap,last_pad_cap_bound_fF=lastcap,last_pad_wire_total_um=64,
            root_CLKQ_fall_minmax_ps=q,INV_rise_minmax_ps=inv,pad_rise_minmax_ps=pad,
            pad_slew_minmax_ps=slew,last_pad_slew_minmax_ps=lastslew,
            release_before_distribution_minmax_ps=[q[0]+inv[0]+3*pad[0]+last[0],q[1]+inv[1]+3*pad[1]+last[1]],
            slew_limit_ps=80,wire_RC_units='fF/um and ohm/um under Liberty1ps/1fF; nominal installed platform RC, not extracted')
        if max(slew[1],lastslew[1])>80:raise ValueError('fixed provider pad violates selected80ps slew bound')
    other=tree_count(reset-90);plain=tree_count(clock-reset);meta=tree_count(90)
    clock_buffers=other['buffers']+plain['buffers']+meta['buffers']+3+15+3
    reset_buffers=other['buffers']+4+3 # existing metadata15 already in live mapped cone
    return dict(schema='QWEN_CURRENT_RESET_CONSTRUCTION_V1',live_source=pins,live_model=selected,
        live_map=dict(service='qrom-fulltile-smin6-map-r1-20261002.service',supervisor=1480247,yosys=1483691,
            work=str(LIVE),source_commit=pins['commit'],gate_commit='3c431937a07a16806825d39b7f6c33541f211691',
            reused=True,additional_maps_launched=0),
        source_inventory=dict(clock_bits=clock,reset_bits=reset,mapped_counts=None,
            scope='Actual current source proc+opt at752fffd8a; does not substitute for mapped survival',
            prior_SMlN_label_correction='Preserved old proc isSMIN6, historical fullmap isSMIN7;6dd censusSMIN7 label was incorrect, retained as history.'),
        provider=dict(source=PROVIDER.as_posix(),source_sha256=sha(PROVIDER),default=0,
            cells={ASR:2,'INVx1_ASAP7_75t_R':2,BUF:5,'AND3x1_ASAP7_75t_R':1},
            root_nominal_area_um2=2*area[ASR]+2*area['INVx1_ASAP7_75t_R']+4*area[BUF],
            launch_join_area_um2=joins['ss']['area_um2'],launch_driver_area_um2=area[BUF],
            protocol='Asyncassert; stage1edge1/stage2edge2; held start firstacceptededge3 if numeric constraints and domainready pass',
            new_queue=False,start_or_data_may_not_be_dropped=True,
            external_reset_deassert_minmax_ps=[100,780],external_reset_low_pulse_min_ps=330,
            clk_and_external_reset_input_slew_minmax_ps=[5,80],launch_minmax_ps=[50,650],
            actual_ib_go_first_mapped_sink=launch_sink[0],
            launch32um_route_is_allocated_not_extracted=True,
            parent_domains_ready='Registered streaming-domain acknowledgment of serial/service release and owned-tag/read/fill retirement; never tie high without source evidence'),
        nominal_RC=dict(source=OUT.as_posix()+'/inputs/setRC.tcl',signal_cap_fF_per_um=wirecap,
            signal_resistance_ohm_per_um=wireres,pad_route_um=32,
            branch_load_cap_ceiling_fF=46.08,buffer_stage_input_slew_range_ps=[5,80],
            tree_branch_slew_limit_ps=320,wire_cap_not_zero=True,extracted=False),
        provider_LUT_envelopes=timing,
        finite_construction=dict(fanout_ceiling=8,other_reset=other,plain_clock=plain,metadata_clock=meta,
            clock_buffers_before_wire_segment_isolation=clock_buffers,
            reset_buffers_before_wire_segment_isolation=reset_buffers,
            paired_ASR_clock_reset_topology=True,existing76BUF_preserved=True,
            macro_clock_branches=12,metadata_and_macro_clock_depth_padding=3,
            wire_segmentation='Each branch adds a driver at parent; RC segment splits until fanout pin+wire<=46.08fF; both clock/reset trees get identical segment/pad geometry. Actual counts from same map, not source WIDTH.',
            nominal_unsegmented_base_area_um2=(clock_buffers+reset_buffers)*area[BUF]+2*area[ASR]+2*area['INVx1_ASAP7_75t_R']+joins['ss']['area_um2']+area[BUF],
            wire_segment_buffer_area_must_be_added=True,final_cell_ceiling_um2=125000,
            reject_if_current_mapped_area_plus_all_constructed_cells_exceeds_ceiling=True),
        memory_clock_loads=dict(tile=C.macro_inventory('ot_rom_4096x266_m8',10),KV=C.macro_inventory('ot_sram_1r1w_128x256_m1_r2c2',2),
            separate_service_tail=obj(OUT/'inputs/ampere_contract_receipt_r1.json')['physical_service_slot']),
        launch_constraints=dict(period_ps=833.3333333333334,setup_uncertainty_ps=60,hold_uncertainty_ps=25,
            first_downstream_accept_edge=3,cold_start_added_edges=2,steady_added_cycles=0,
            actual_wrom_addr_register_bits=24,actual_wrom_re_register_bits=1,
            address_FF_min_arrival_plus_distribution_minus_skew_ps=42.422199,
            reset_FF_min_arrival_plus_distribution_minus_skew_ps=50.049297,
            root_external_pin_removal_margin_ps=100-92.5064,root_external_pin_recovery_margin_ps=791.5025333333334-780,
            SS_FF_CLKQ_and_distribution='Characterized Liberty envelopes only; rejected mapped survival prevents contextual timing measurement. External pin bounds are implementation requirements, not observed arrivals.'),
        admission=dict(provider_source_constructed=True,current_single_map_already_admitted=True,
            installed_CTS_required_before_context=False,contextual_SSFF=False,PnR=False,hardware_adoption=False,
            actual_timed_production_KV_policy=False,cold_KV_calendar_is_production=False),
        remaining_parent_composition=dict(
            external_root_intervals='Implemented provider has numeric pin requirements; actual parent source/route arrivals have not been observed.',
            producer_arrivals='ROM captures and early select proven by graph/source attribution. High-address and KV semantic joins remain open; physical mask/bank replicas failed retention. No producer launch timing admission.',
            rank_release='parent_domains_ready requires owned retirement plus registered stream acknowledgment of serial/service release; source is not tied to an assumed constant.',
            ordered_movement='Persistent KV causal/slot receipt is included; complete forward/reverse grant traversal and release remain unadmitted.',
            once_only_calendar='No selected production current once-only calendar is supplied by this provider; cold calendar remains reference.',
            current_r33_lowered_window='Parent adapter integration is separate; this receipt provides no lowered-window timing or movement credit.'))


def construct(net, metadata_expected=90):
    """Construct the actual finite clock/reset graph around completed map bytes.

    New buffers use bounded nominal RC geometry, not zero wire capacitance.
    The original76 buffers and all arithmetic/FF/data nets remain intact.
    """
    import copy
    net=copy.deepcopy(net);cells=net['cells'];ports=net['ports']
    clk=ports['clk_stream']['bits'][0];rst=ports['reset_stream_n']['bits'][0]
    go=ports['ib_go']['bits'][0]
    nextbit=max(b for c in cells.values() for v in c['connections'].values() for b in v if isinstance(b,int))+1
    added={};coords={};wire_edges=[];roots={};original=set(cells)
    def fresh():
        nonlocal nextbit
        b=nextbit;nextbit+=1;return b
    release=fresh();ready=fresh();joined_go=fresh()
    ports['external_reset_n']=ports.pop('reset_stream_n')
    ports['parent_domains_ready']=dict(direction='input',bits=[ready])
    for name in original:
        for pin,bits in cells[name]['connections'].items():
            cells[name]['connections'][pin]=[joined_go if b==go else b for b in bits]
    reset_ff=[];plain=[];macros=[];metadata=[];resetpin={}
    for n in sorted(original):
        c=cells[n];con=c['connections']
        if c['type'].startswith('DFF'):
            if con.get('CLK')!=[clk]:raise ValueError('unbound actual clock domain')
            if c['type']==ASR:
                direct=[p for p in ('RESETN','SETN') if con.get(p)==[rst]]
                if len(direct)==1:reset_ff.append(n);resetpin[n]=direct[0]
                else:metadata.append(n)
            else:plain.append(n)
        elif c['type'] in ('ot_rom_4096x266_m8','ot_sram_1r1w_128x256_m1_r2c2'):macros.append(n)
    if len(macros)!=12 or len(metadata)!=metadata_expected:raise ValueError('actual complete10ROM2KV/90metadata binding failed')
    selected=obj(OUT/'inputs/model.json');width=selected['slot']['w_um'];height=selected['slot']['h_um']
    # Two logic strips, kept out of reserved central fill corridor. Half-group
    # ordering keeps low tree levels on one side of the corridor.
    def positions(names):
        half=math.ceil(len(names)/2);rows=max(1,math.ceil(half/32))
        for i,n in enumerate(names):
            side=int(i>=half);j=i%half
            coords[n]=(4.32+side*(width/2+selected['corridor']['width_um']/2)+((j%32)+.5)*3.5,
                       393.12+((j//32)+.5)*(height-397.44)/rows)
    positions(reset_ff);positions(plain);positions(metadata)
    for i,n in enumerate(macros):coords[n]=(4.32+(i%2)*(width-130.464),2.16+(i//2)*69.12)
    def connect(source,targets,label,pos):
        out=fresh();cells[label]=dict(type=BUF,connections=dict(A=[source],Y=[out]));added[label]=cells[label];coords[label]=pos
        for n,p in targets:cells[n]['connections'][p]=[out]
        return out
    def tree(targets,source,label):
        level=0
        while targets:
            parents=[]
            for i in range(0,len(targets),8):
                children=targets[i:i+8];position=tuple(sum(coords[n][d] for n,p in children)/len(children) for d in (0,1))
                name=f'context_{label}_L{level}_{i//8}';connect(source,children,name,position);parents.append((name,'A'))
            if len(parents)==1:roots[label]=parents[0][0];return level+1
            targets=parents;level+=1
        raise ValueError('empty clock/reset branch')
    depth={}
    depth['reset_clock']=tree([(n,'CLK') for n in reset_ff],clk,'reset_clock')
    depth['plain_clock']=tree([(n,'CLK') for n in plain],clk,'plain_clock')
    depth['metadata_clock']=tree([(n,'CLK') for n in metadata],clk,'metadata_clock')
    depth['other_reset']=tree([(n,resetpin[n]) for n in reset_ff],release,'other_reset')
    macro_leaves=[]
    for i,n in enumerate(macros):
        name=f'context_macro_leaf_{i}';connect(clk,[(n,'clk')],name,coords[n]);macro_leaves.append((name,'A'))
    depth['macro_clock']=1+tree(macro_leaves,clk,'macro_clock')
    target_depth=max(v for k,v in depth.items() if k!='other_reset')
    for label in ('plain_clock','metadata_clock','macro_clock'):
        root=roots[label]
        for p in range(target_depth-depth[label]):
            name=f'context_align_{label}_{p}';connect(clk,[(root,'A')],name,coords[root]);root=name
        roots[label]=root
    # The original metadata reset tree is3buffers. Match its total depth to
    # its clock path, in addition to the4 physical root release delay pads.
    metadata_roots=[(n,'A') for n in original if cells[n]['type']==BUF and cells[n]['connections'].get('A')==[rst]]
    if not metadata_roots:raise ValueError('existing metadata reset roots missing')
    meta_source=release
    for p in range(target_depth-3):
        name=f'context_metadata_reset_align_{p}'
        meta_source=connect(meta_source,[],name,(width/2,height/2))
        if p>0:cells[name]['connections']['A']=[last]
        last=meta_source
    for n,p in metadata_roots:
        cells[n]['connections'][p]=[meta_source];coords[n]=(width/2,height/2)
    cells['context_provider']=dict(type='ot_qwen_rom_reset_parent_provider',parameters=dict(RESET_CONTEXT=1),
        connections=dict(clk_stream=[clk],external_reset_n=[rst],parent_domains_ready=[ready],ib_go=[go],
                         released_reset_n=[release],launch_enable=[joined_go]))
    rc=price()['nominal_RC']
    caps={c:library(c)[2] for c in ('ss','ff')};coef=rc['signal_cap_fF_per_um']
    # Each BUF output gets local branch drivers, each long branch segmented
    # into<=128um nominal routes. Parent sees fanout<=8 and16um local routes;
    # a branch driver sees one next pin plus<=128um wire. Clock/reset paired
    # topologies have the same coordinates and therefore the same segments.
    coords['context_provider']=(width/2,height/2)
    drivers={c['connections']['Y'][0]:n for n,c in cells.items() if n in added}
    drivers[release]='context_provider'
    sinks=collections.defaultdict(list)
    for n,c in list(cells.items()):
        for pin,bits in c['connections'].items():
            if (n in added and pin=='A') or (n in original and (pin in ('CLK','clk','RESETN','SETN') or (pin=='A' and c['type']==BUF))):
                if len(bits)==1 and bits[0] in drivers:sinks[drivers[bits[0]]].append((n,pin))
    for parent,targets in list(sinks.items()):
        out=release if parent=='context_provider' else cells[parent]['connections']['Y'][0]
        for i,(child,pin) in enumerate(targets):
            pos=coords[parent];end=coords[child]
            isolation=f'{parent}_branch{i}'
            signal=connect(out,[],isolation,pos);wire_edges.append(dict(driver=parent,sink=isolation,pin='A',length_um=16))
            distance=max(16,abs(end[0]-pos[0])+abs(end[1]-pos[1]))
            segments=math.ceil(distance/128)
            previous=isolation
            for k in range(1,segments):
                name=f'{isolation}_segment{k}'
                position=tuple(pos[d]+(end[d]-pos[d])*k/segments for d in (0,1))
                signal=connect(signal,[],name,position)
                wire_edges.append(dict(driver=previous,sink=name,pin='A',length_um=distance/segments));previous=name
            cells[child]['connections'][pin]=[signal]
            wire_edges.append(dict(driver=previous,sink=child,pin=pin,length_um=distance/segments))
    loads={};slews={}
    edges_by_driver=collections.defaultdict(list)
    for edge in wire_edges:edges_by_driver[edge['driver']].append(edge)
    for corner in ('ss','ff'):
        raw,lib,cap=library(corner);buf=lib[BUF]
        for name in added:
            edges=edges_by_driver[name]
            load=sum(e['length_um']*coef+cap[(cells[e['sink']]['type'],e['pin'])]['cap_fF'] for e in edges)
            if not edges:continue
            if not 2.88<=load<=46.08:raise ValueError('constructed branch violates characterized load bound '+name)
            rise=envelope(buf,'rise_transition',load,5,320);fall=envelope(buf,'fall_transition',load,5,320)
            if max(rise[1],fall[1])>320:raise ValueError('constructed branch violates slew bound')
            loads[corner+':'+name]=load;slews[corner+':'+name]=max(rise[1],fall[1])
    return dict(net=net,added_buffers=len(added),actual_reset_FF=len(reset_ff),actual_plain_FF=len(plain),
        actual_reset_pin_classes=dict(collections.Counter(resetpin.values())),metadata_FF=len(metadata),macro_CLK_sinks=12,
        provider_release_net=release,wire_edges=wire_edges,nominal_wire_cap_fF=sum(e['length_um']*coef for e in wire_edges),
        max_branch_load_fF=max(loads.values()),max_branch_slew_ps=max(slews.values()),
        nominal_wire_elmore_bound_ps=max((rc['signal_resistance_ohm_per_um']*e['length_um']*(coef*e['length_um']/2+max(caps[c][(cells[e['sink']]['type'],e['pin'])]['cap_fF'] for c in ('ss','ff')))/1000 for e in wire_edges),default=0),
        node_coordinates_um=coords,wire_cap_assigned=True,nominal_not_extracted=True,
        ready_for_contextual_STA=True,installed_CTS_required=False,physical_admission=False,
        topology_is_nominal_allocation_not_routed_geometry=True,
        startup_two_edges_is_conditional_on_complete_distribution_timing=True)


def write_verilog(result,path):
    net=result['net'];cells=net['cells'];ports=net['ports']
    def identifier(name):return name if re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*',name) else '\\'+name+' '
    def bit(b):return 'ctx_n'+str(b) if isinstance(b,int) else "1'b"+str(b)
    def vector(bits):return bit(bits[0]) if len(bits)==1 else '{'+','.join(bit(b) for b in reversed(bits))+'}'
    name='qwen_fulltile_constructed_context'
    lines=['module '+name+'('+','.join(identifier(p) for p in ports)+');']
    used={b for c in cells.values() for v in c['connections'].values() for b in v if isinstance(b,int)}
    lines += ['wire '+','.join('ctx_n'+str(b) for b in sorted(used))+';']
    for p,row in ports.items():
        width='' if len(row['bits'])==1 else '['+str(len(row['bits'])-1)+':0] '
        lines.append(row['direction']+' wire '+width+identifier(p)+';')
        if row['direction']=='input':lines.append('assign '+vector(row['bits'])+'='+identifier(p)+';')
        else:lines.append('assign '+identifier(p)+'='+vector(row['bits'])+';')
    for n,c in cells.items():
        params=' #(.RESET_CONTEXT(1))' if c['type']=='ot_qwen_rom_reset_parent_provider' else ''
        lines.append(c['type']+params+' '+identifier(n)+'('+','.join('.'+p+'('+vector(v)+')' for p,v in c['connections'].items())+');')
    lines.append('endmodule');path.write_text('\n'.join(lines)+'\n')


def assess_existing_map(work):
    """Read the ONE preserved map and replay the pinned survival predicates.

    $scopeinfo is counted as metadata, never discarded from original evidence.
    This assessment gives no PASS override to a failed terminal.
    """
    pins=json.loads((work/'sourcepins.json').read_text())
    if pins['commit']!='752fffd8a7dd31742f383ca59b89598db51d7222':raise ValueError('different live source')
    terminal=json.loads((work/'terminal.json').read_text())
    net=json.loads((work/'mapped.json').read_text())['modules']['ot_qwen_rom_fulltile_tp4_context_top']
    spec=importlib.util.spec_from_file_location('pinned_gate',ROOT/OUT/'inputs/qwen_rom_fulltile_mapped_gate.py')
    gate=importlib.util.module_from_spec(spec);spec.loader.exec_module(gate)
    base=r'u_tile\.u_logic\.'
    targets={
        'ROM_capture':(base+r'g_pair\[[01]\]\.g_bank\[[0-4]\]\.g_cap\.g_direct\.cap',2560),
        'mask':(base+r'g_pair\[[01]\]\.g_bank\[[0-4]\]\.g_cap\.g_direct\.g_mask\[[0-7]\]\.local_sel',80),
        'bank_strobe':(base+r'code_rd_bank',5),
        'early_select':(base+r'code_sel_q',5),
        'KV_capture':(base+r'g_kv_local\.g_kvcap\.cap',512),
        'address_producer':(base+r'u_me\.wrom_addr',24),
        'read_producer':(base+r'u_me\.wrom_re',1)}
    survival={}
    for name,(pattern,expected) in targets.items():
        bits=[b for n,row in net['netnames'].items() if re.fullmatch(pattern,n) for b in row['bits']]
        row=dict(expected_bits=expected,observed_bits=len(bits),pattern=pattern)
        try:
            if len(bits)!=expected:raise ValueError('missing target register nets')
            endpoints=gate.ff_endpoints(net,bits)
            row.update(status='PASS_ENDPOINT_SURVIVAL_ONLY',endpoint_count=len(endpoints),endpoint_sha256=hashlib.sha256(canon(endpoints)).hexdigest())
        except ValueError as e:row.update(status='FAIL_RETAINED',reason=str(e))
        survival[name]=row
    types=collections.Counter(c['type'] for c in net['cells'].values())
    clock=net['ports']['clk_stream']['bits'][0];reset=net['ports']['reset_stream_n']['bits'][0]
    counts=collections.Counter()
    for cell in net['cells'].values():
        con=cell['connections']
        if cell['type'].startswith('DFF'):
            counts['clock_FF']+=1;counts['stream_clock_FF']+=con.get('CLK')==[clock]
            if cell['type']==ASR:
                direct=any(con.get(p)==[reset] for p in ('RESETN','SETN'))
                counts['direct_parent_reset_FF' if direct else 'distributed_metadata_reset_FF']+=1
    library_text=(work/'ss_merged.lib').read_text()
    areas={m[1]:float(re.search(r'area\s*:\s*([\d.]+)',C.block(library_text,m.start()))[1]) for m in re.finditer(r'\bcell\s*\(([^)]+)\)',library_text)}
    return dict(schema='QWEN_CURRENT_SINGLE_MAP_ASSESSMENT_V1',
        status='FAIL_RETAINED_NO_CONTEXTUAL_ADMISSION',original_terminal=terminal,
        source_commit=pins['commit'],SMIN=pins['SMIN'],
        original_files={n:dict(sha256=hashlib.sha256((work/n).read_bytes()).hexdigest(),bytes=(work/n).stat().st_size) for n in ('terminal.json','mapped.json','mapped.v','sourcepins.json','model.json','ss_merged.lib')},
        endpoint_survival=survival,actual_mapped_FF_counts=dict(counts),
        macro_counts={n:types[n] for n in ('ot_rom_4096x266_m8','ot_sram_1r1w_128x256_m1_r2c2')},
        source_distribution_buffers=sum('.u_tree.' in n and c['type']==BUF for n,c in net['cells'].items()),
        scopeinfo_metadata_cells=types['$scopeinfo'],
        standard_cell_area_um2=sum(areas.get(c['type'],0) for c in net['cells'].values()),
        standard_cell_area_excludes_macros_and_metadata=True,
        contextual_SSFF=False,constructed_complete_tile=False,physical_admission=False,
        additional_maps_launched=0,terminal_overwritten=False,
        disposition='Reject this source-matched map for contextual implementation. Root source and prospective finite distribution model remain separate, unadopted implementation inputs.')


def inventory_existing_map(work,out):
    """Actual mapped pin load census, including the failed map's surviving FFs.
    Macro ports are inventoried once; persistent service state is separate.
    """
    pins=json.loads((work/'sourcepins.json').read_text())
    if pins['commit']!='752fffd8a7dd31742f383ca59b89598db51d7222':raise ValueError('different map source')
    net=json.loads((work/'mapped.json').read_text())['modules']['ot_qwen_rom_fulltile_tp4_context_top']
    caps={corner:library(corner)[2] for corner in ('ss','ff')}
    clk=net['ports']['clk_stream']['bits'][0];rst=net['ports']['reset_stream_n']['bits'][0]
    rows=[];totals=collections.defaultdict(lambda:dict(pins=0,ss_cap_fF=0.,ff_cap_fF=0.))
    constant_reset_pins=0
    for name,cell in sorted(net['cells'].items()):
        kind=cell['type'];con=cell['connections']
        if kind.startswith('DFF'):
            selected=['CLK']+[p for p in ('RESETN','SETN') if p in con]
        elif kind in ('ot_rom_4096x266_m8','ot_sram_1r1w_128x256_m1_r2c2'):selected=['clk']
        else:continue
        for pin in selected:
            bits=con[pin]
            if len(bits)!=1:raise ValueError('clock/reset pin width invalid')
            b=bits[0]
            if pin in ('RESETN','SETN') and not isinstance(b,int):constant_reset_pins+=1;continue
            if pin in ('CLK','clk') and b!=clk:raise ValueError('unbound mapped clock domain')
            group=('logic_clock' if pin=='CLK' else 'ROM_clock' if kind.startswith('ot_rom') else 'KV_clock') if pin in ('CLK','clk') else ('direct_parent_reset' if b==rst else 'distributed_reset')
            load={c:caps[c][(kind,pin)]['cap_fF'] for c in ('ss','ff')}
            row=dict(instance=name,cell=kind,pin=pin,net_bit=b,clock_domain='stream_1p2GHz',group=group,nominal_pin_cap_fF=load)
            rows.append(row);totals[group]['pins']+=1
            for c in ('ss','ff'):totals[group][c+'_cap_fF']+=load[c]
    census=out/'mapped-sink-census-r1.json.gz'
    if census.exists():raise ValueError('refuse overwrite mapped census')
    census.write_bytes(gzip.compress(canon(rows),mtime=0))
    receipt=dict(schema='QWEN_CURRENT_MAPPED_SINK_LOADS_V1',source_commit=pins['commit'],
        original_mapped_sha256=hashlib.sha256((work/'mapped.json').read_bytes()).hexdigest(),
        original_terminal=json.loads((work/'terminal.json').read_text()),
        mapped_survival_qualified=False,groups=dict(totals),constant_reset_set_pins=constant_reset_pins,
        census_sha256=hashlib.sha256(census.read_bytes()).hexdigest(),census_records=len(rows),
        caps_are_pins_only=True,wire_construction='Prospective construction prices nominal RC separately. Failed survival forbids a complete instantiated tile.',
        persistent_KV_service_tail_clock_domain='Independent service;384+128macro clock ports/rank remain separate from tile10ROM+2KV.',
        hardware_admission=False)
    (out/'mapped-loads-r1.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')


def reconcile_graph():
    classification=obj(OUT/'inputs/euclid-classification-r1.json')
    graph=obj(OUT/'inputs/euclid-graph-survival-r3.json')
    digest='92b6cf36af938f89468c6ce07d7bd5624239172eecd914de3eb750ff435802a0'
    if classification['raw_mapped_json_SHA256']!=digest or graph['raw_mapped_sha256']!=digest:raise ValueError('different graph/map bytes')
    checks=graph['endpoint_checks']
    if classification['actual_ROM_capture_FFs']!=2560 or classification['actual_early_select_FFs']!=5:raise ValueError('incomplete current capture/source attribution')
    missing_mask=80-checks['mask']['unique_FF_count'];missing_bank=5-checks['bank_strobe']['unique_FF_count']
    if (missing_mask,missing_bank)!=(50,3):raise ValueError('different replica deficit')
    added=missing_mask+missing_bank
    _,cells,caps=library('ss')
    area=float(re.search(r'area\s*:\s*([\d.]+)',cells[ASR])[1])
    direct=56593;plain=45657;metadata=37+added
    other=tree_count(direct);plain_tree=tree_count(plain);meta_tree=tree_count(metadata)
    clockbuf=other['buffers']+plain_tree['buffers']+meta_tree['buffers']+3+15+3
    resetbuf=other['buffers']+3+4
    pin_delta={corner:{pin:added*library(corner)[2][(ASR,pin)]['cap_fF'] for pin in ('CLK','RESETN')} for corner in ('ss','ff')}
    return dict(schema='QWEN_CURRENT_GRAPH_RECONCILIATION_V1',original_mapped_sha256=digest,
        hardware_source_commit=classification['source_commit'],original_collector_FAIL_retained=True,
        graph_gate_status=graph['status'],physical_replica_retention='FAIL_REQUIRED_PHYSICAL_REPLICA_RETENTION',
        actual_ROM_capture_FFs=2560,actual_early_select_FFs=5,
        named_wire_diagnostic_correction='Missing cap/code_sel_q names do not imply missing FFs. Old r1 named-wire failures retained as diagnostic history only.',
        mask_FFs=dict(required=80,actual=30,missing=missing_mask),bank_strobe_FFs=dict(required=5,actual=2,missing=missing_bank),
        KV_and_high_address='Source-provenance present; named-wire diagnostics do not prove missing hardware. Complete semantic source-to-driver join remains open.',
        minimum_replica_preservation=dict(additional_ASR_FFs=added,nominal_cell_area_um2=added*area,
            added_pin_load_fF=pin_delta,RTL_or_mapped_replica_restoration_performed=False,
            repaired_clock_FFs=102287+added,repaired_ASR_FFs=56630+added,metadata_reset_FFs=metadata,
            source_WIDTH_budget_unchanged=True,new_mapping_run=False),
        source_matched_after_preservation_distribution=dict(
            other_reset=other,plain_clock=plain_tree,metadata_clock=meta_tree,fanout_ceiling=8,
            clock_buffers_before_wire_segmentation=clockbuf,reset_buffers_including4rootpads_before_wire_segmentation=resetbuf,
            paired_other_reset_clock_topology=True,original76BUF_retained=True,source_tree_clock_depth=6,
            new_cell_area_before_wire_segmentation_um2=(clockbuf+resetbuf)*.10206+2*area+2*.04374+.08748+.10206,
            wire_isolation_and_segments_must_be_constructed_and_added=True,physical_admission=False),
        original_standard_cell_area_um2=classification['cell_area_um2'],complete_cell_ceiling_um2=125000,
        corridor=dict(width_um=96.768,fill_tracks=1048,clock_reserved_tracks=64,reset_reserved_tracks=64,spare_tracks=184),
        finite_PG_and_cut_requirements=dict(PDN_via_OBS_share=.5,measured_PDN_cut_capacity=None,
            reserved_clock_reset_tracks_each=64,fill_channel_uses1048tracks=True,
            construction_not_a_routed_PG_proof=True),
        source_pin_requirements=dict(address_min_arrival_plus_wire_minus_clock_skew_ps=42.422199,
            metadata_reset_min_arrival_plus_wire_minus_clock_skew_ps=50.049297,
            setup_uncertainty_ps=60,hold_uncertainty_ps=25),
        admission=dict(contextual_SSFF=False,full_tile_construction=False,second_map=False,PnR=False))


def allocate_failed_map(work,out):
    """Finite branch allocation for the actual failed map's surviving sinks.

    Emits analytical net edits/wires only. No RTL, synthesis or timing run.
    Preservation53 and old76-buffer wire timing remain separately priced.
    """
    assessment=json.loads((out/'single-map-assessment-r1.json').read_text())
    if hashlib.sha256((work/'mapped.json').read_bytes()).hexdigest()!=assessment['original_files']['mapped.json']['sha256']:raise ValueError('different mapped bytes')
    net=json.loads((work/'mapped.json').read_text())['modules']['ot_qwen_rom_fulltile_tp4_context_top']
    expected=assessment['actual_mapped_FF_counts']['distributed_metadata_reset_FF']
    result=construct(net,metadata_expected=expected)
    old=set(net['cells']);added={n:c for n,c in result['net']['cells'].items() if n not in old}
    edits={n:{pin:bits for pin,bits in row['connections'].items() if bits!=net['cells'][n]['connections'][pin]} for n,row in result['net']['cells'].items() if n in old}
    edits={n:v for n,v in edits.items() if v}
    payload=dict(added_primitive_cells=added,original_cell_pin_edits=edits,wire_edges=result['wire_edges'],nominal_node_coordinates_um=result['node_coordinates_um'])
    artifact=out/'asbuilt-finite-allocation-r1.json.gz'
    if artifact.exists():raise ValueError('refuse overwrite finite allocation')
    artifact.write_bytes(gzip.compress(canon(payload),mtime=0))
    selected=obj(OUT/'inputs/model.json');center=selected['slot']['w_um']/2;half=selected['corridor']['width_um']/2
    cut_counts={}
    for cut in (center-half,center,center+half):
        crossing=collections.defaultdict(set)
        for e in result['wire_edges']:
            x1=result['node_coordinates_um'][e['driver']][0];x2=result['node_coordinates_um'][e['sink']][0]
            if min(x1,x2)<cut<=max(x1,x2):
                kind='clock' if 'clock' in e['driver'] or 'macro' in e['driver'] else 'reset'
                crossing[kind].add(e['driver'])
        cut_counts[str(cut)]={k:len(v) for k,v in crossing.items()}
    provider=price()['provider'];increment=result['added_buffers']*.10206+provider['root_nominal_area_um2']+provider['launch_join_area_um2']+provider['launch_driver_area_um2']
    record={k:v for k,v in result.items() if k not in ('net','node_coordinates_um','wire_edges')}
    record.update(schema='QWEN_ACTUAL_FAILED_MAP_FINITE_ALLOCATION_V1',scope='Actual surviving mapped sinks; analytical branch construction only, not selected RTL or repaired map.',
        original_mapped_sha256=assessment['original_files']['mapped.json']['sha256'],source_commit=assessment['source_commit'],
        added_buffers=result['added_buffers'],nominal_incremental_cell_area_um2=increment,
        original_cell_area_um2=assessment['standard_cell_area_um2'],
        nominal_area_after_preservation53_um2=assessment['standard_cell_area_um2']+increment+53*.37908,
        final_area_includes_preservation_distribution=False,
        cell_area_ceiling_um2=125000,wire_edges=len(result['wire_edges']),
        allocation_sha256=hashlib.sha256(artifact.read_bytes()).hexdigest(),
        unique_new_branch_nets_crossing_vertical_cuts=cut_counts,clock_reset_tracks_reserved_each=64,
        old76BUF_internal_routes_not_in_this_new_branch_census=True,
        current_PDN_cut_capacity_measured=False,PG_via_OBS_reserved_fraction=.5,
        finite_graph_does_not_prove_route_or_complete_timing=True,
        ready_for_contextual_STA=False,failed_source_survival_retained=True,
        missing53_replicas_instantiated=False,new_RTL_or_map_run=False,
        physical_admission=False)
    (out/'asbuilt-finite-allocation-receipt-r1.json').write_text(json.dumps(record,indent=2,sort_keys=True)+'\n')


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,default=ROOT/OUT)
    parser.add_argument('--construct-existing-map',type=Path)
    parser.add_argument('--assess-existing-map',type=Path)
    parser.add_argument('--inventory-existing-map',type=Path)
    parser.add_argument('--allocate-failed-map',type=Path)
    args=parser.parse_args()
    from uarch_model_qwen_current_reset import qwen_rom_current_reset_price
    args.out.mkdir(parents=True,exist_ok=True);p=qwen_rom_current_reset_price()
    if args.inventory_existing_map:inventory_existing_map(args.inventory_existing_map,args.out)
    if args.assess_existing_map:
        dest=args.out/'single-map-assessment-r1.json'
        if dest.exists():raise ValueError('refuse overwrite immutable map assessment')
        assessment=assess_existing_map(args.assess_existing_map)
        dest.write_text(json.dumps(assessment,indent=2,sort_keys=True)+'\n')
    graph=reconcile_graph()
    p['actual_graph_reconciliation']=graph
    (args.out/'graph-reconciliation-r1.json').write_text(json.dumps(graph,indent=2,sort_keys=True)+'\n')
    assessment_path=args.out/'single-map-assessment-r1.json'
    if assessment_path.exists():
        assessment=json.loads(assessment_path.read_text())
        p['source_inventory']['mapped_counts']=assessment['actual_mapped_FF_counts']
        p['live_map']['terminal_status']=assessment['original_terminal']['status']
        p['live_map']['survival_status']=assessment['status']
        p['admission']['mapped_survival']=False
    loads_path=args.out/'mapped-loads-r1.json'
    if loads_path.exists():p['actual_mapped_sink_loads']=json.loads(loads_path.read_text())
    if args.allocate_failed_map:allocate_failed_map(args.allocate_failed_map,args.out)
    allocated=args.out/'asbuilt-finite-allocation-receipt-r1.json'
    if allocated.exists():p['actual_surviving_sink_finite_allocation']=json.loads(allocated.read_text())
    if args.construct_existing_map:
        work=args.construct_existing_map
        terminal=json.loads((work/'terminal.json').read_text())
        if terminal['status']!='PASS_COMPLETE_SOURCE_MAP_ONLY_CONTEXT_OPEN':raise ValueError('single map not complete/PASS')
        pins=json.loads((work/'sourcepins.json').read_text())
        if pins['commit']!=p['live_map']['source_commit']:raise ValueError('different map source')
        assessment=assess_existing_map(work)
        if any(row['status']=='FAIL_RETAINED' for row in assessment['endpoint_survival'].values()):
            raise ValueError('required actual mapped capture/producer survival failed')
        result=construct(json.loads((work/'mapped.json').read_text())['modules']['ot_qwen_rom_fulltile_tp4_context_top'])
        full_library=(work/'ss_merged.lib').read_text()
        bufarea=float(re.search(r'area\s*:\s*([\d.]+)',C.block(full_library,full_library.index('cell ('+BUF+')')))[1])
        context_area=result['added_buffers']*bufarea+p['provider']['root_nominal_area_um2']+p['provider']['launch_join_area_um2']+p['provider']['launch_driver_area_um2']
        final_area=terminal['mapped_cell_area_um2']+context_area
        receipt={k:v for k,v in result.items() if k not in ('net','node_coordinates_um','wire_edges')}
        receipt.update(original_map_sha256=hashlib.sha256((work/'mapped.json').read_bytes()).hexdigest(),
            context_area_um2=context_area,complete_area_um2=final_area,complete_cell_ceiling_um2=125000,
            area_fit=final_area<=125000)
        name='constructed-context-r1'
        if (args.out/(name+'.v')).exists():raise ValueError('refuse overwrite constructed context')
        write_verilog(result,args.out/(name+'.v'))
        (args.out/(name+'-wires.json.gz')).write_bytes(gzip.compress(canon(dict(edges=result['wire_edges'],node_coordinates=result['node_coordinates_um'])),mtime=0))
        (args.out/(name+'-receipt.json')).write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
        if final_area>125000:raise ValueError('constructed context exceeds selected cell ceiling; FAIL retained')
    (args.out/'model-r1.json').write_text(json.dumps(p,indent=2,sort_keys=True)+'\n')
    sdc='''create_clock -name stream -period 833.3333333333334 [get_ports clk_stream]
set_clock_uncertainty -setup 60 [get_clocks stream]
set_clock_uncertainty -hold 25 [get_clocks stream]
set_clock_transition 40 [get_clocks stream]
set_input_transition 40 [get_ports external_reset_n]
set_input_delay -clock stream -min 100 [get_ports external_reset_n]
set_input_delay -clock stream -max 780 [get_ports external_reset_n]
set_input_delay -clock stream -min 50 [get_ports {ib_go parent_domains_ready}]
set_input_delay -clock stream -max 650 [get_ports {ib_go parent_domains_ready}]
set_input_transition 40 [get_ports {ib_go parent_domains_ready}]
# Root pin intervals are requirements at BOTH provider RESETN pins.
# Parent reset fanout/route must preserve them; these are not measured arrivals.
# Low RESETN pulse >=330ps at both provider pins.
# Inputs remain stable until first accepted edge; all grants/tags are owned.
# Complete-tile payload constraints (use in complete constructed context only):
# set_input_delay -clock stream -min 50 [get_ports {tile_id* ib[*] xl[*] n_y[*] n_vy kvw_ce kvw_addr[*] kvw_data[*] kvw_mask[*]}]
# set_input_delay -clock stream -max 650 [get_ports {tile_id* ib[*] xl[*] n_y[*] n_vy kvw_ce kvw_addr[*] kvw_data[*] kvw_mask[*]}]
# set_input_transition 40 [get_ports {tile_id* ib[*] xl[*] n_y[*] n_vy kvw_ce kvw_addr[*] kvw_data[*] kvw_mask[*]}]
# No falsepaths or waived recovery/removal. Loads and wireRC assigned by graph.
'''
    (args.out/'provider-constraints-r1.sdc').write_text(sdc)
    paths=[Path(__file__).relative_to(ROOT),PROVIDER,Path('tools/uarch_model_qwen_current_reset.py'),
           Path('tools/uarch_model.py'),Path('tools/uarch_model_qwen_reset.py'),RESET/'model-r5.json',
           Path('tools/qwen_rom_physical_context_contract.py'),
           Path('tests/test_qwen_rom_current_reset_construction.py')]
    paths += [x for x in (ROOT/OUT/'inputs').glob('*') if x.is_file()]+list((ROOT/RESET/'inputs').glob('seq_*.lib.gz'))+list((ROOT/RESET/'inputs').glob('invbuf_*.lib.gz'))
    for n in ('ot_rom_4096x266_m8','ot_sram_1r1w_128x256_m1_r2c2'):
        paths += [Path('physical/asap7_memory_macros')/n/(n+s) for s in ('_ss.lib','_ff.lib','.lef')]
    pins={str(x.relative_to(ROOT) if x.is_absolute() else x):sha(x) for x in paths}
    (args.out/'sourcepins-r1.json').write_text(json.dumps(dict(sha256=pins),indent=2,sort_keys=True)+'\n')
    hashes={x.name:hashlib.sha256(x.read_bytes()).hexdigest() for x in args.out.iterdir() if x.is_file() and x.name!='artifact-sha256-r1.json'}
    (args.out/'artifact-sha256-r1.json').write_text(json.dumps(hashes,indent=2,sort_keys=True)+'\n')

if __name__=='__main__':main()
