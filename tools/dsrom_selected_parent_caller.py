"""Static source-exact selected parent binding; no HDL build or RTL execution."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import dsrom_selector_station_parent_binding as S

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'results/uarch/dsrom_selected_parent_caller_20261002'

def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def extract_boundary(raw):
    """Deterministic reduction of retained actual pin-load JSON, no hardware."""
    source=json.loads((BASE/'inputs/actual_boundary_pin_summary.json').read_text())
    if hashlib.sha256(raw).hexdigest()!=source['raw_sha256']:raise ValueError('wrong boundary source')
    d=json.loads(raw);result={}
    for kind,c in d['cases'].items():
        result[kind]={}
        for name,p in c['ports'].items():
            if p['direction']!='input' or name in ('clk','rst_n'):continue
            bits=[]
            for a,z in zip(p['actual_pin_loads']['ss'],p['actual_pin_loads']['ff']):
                if a['bit']!=z['bit'] or a['sink_count']!=z['sink_count']:raise ValueError('corner pin identity differs')
                bits.append(dict(bit=a['bit'],SS_cap_fF=a['load_fF'],FF_cap_fF=z['load_fF'],sink_count=a['sink_count']))
            if len(bits)!=p['width']:raise ValueError('incomplete pin width')
            result[kind][name]=dict(width=p['width'],bits=bits)
    return dict(commit=source['commit'],path=source['path'],raw_sha256=source['raw_sha256'],cases=result)

def finite_parent():
    """Positive construction, conditional timing domains, no wire admission."""
    import gzip, math
    for name,h in json.loads((BASE/'inputs/physical_input_hashes.json').read_text()).items():
        if digest(BASE/'inputs'/name)!=h:raise ValueError('physical input changed: '+name)
    raw,_=S.load();ss=json.loads(raw['SS_driver_cells.json'])['cell_bodies'];ff=json.loads(raw['FF_driver_cells.json'])['cell_bodies']
    b='BUFx4_ASAP7_75t_R';d='DFFHQNx1_ASAP7_75t_R'
    bp=max(S.cap(ss[b],'A'),S.cap(ff[b],'A'))
    profiles=json.loads((BASE/'inputs/clock_pin_profiles.json').read_text())
    actual=json.loads((BASE/'inputs/actual_boundary_pin_summary.json').read_text())
    gate=json.loads((BASE/'inputs/GO_gate_cell.json').read_text())
    lib=(BASE/'inputs/source_simple_ss.lib.gz').read_bytes()
    if hashlib.sha256(lib).hexdigest()!=gate['source_sha256']:raise ValueError('GO source library changed')
    s=gzip.decompress(lib).decode();m=re.search(r'\bcell\s*\(AND2x2_ASAP7_75t_R\)\s*\{',s)
    if S.block(s,m.start())!=gate['cell_body']:raise ValueError('GO cell is not source exact')
    go=max(S.lut(gate['cell_body'],k,80,5.76) for k in ('cell_rise','cell_fall'))
    T=1000/1.2;R=.031287;C=.178475
    cq=max(S.lut(ss[d],k,320,5.76) for k in ('cell_rise','cell_fall'))
    first=max(S.lut(ss[b],k,160,11.52) for k in ('cell_rise','cell_fall'))
    later=max(S.lut(ss[b],k,80,11.52) for k in ('cell_rise','cell_fall'))
    setup=S.constraint(ss[d],'setup_rising')
    wire=R*((11.52-bp)/C)*((11.52-bp)/2+bp)+2*.0172*11.52
    initial=R*((5.76-bp)/C)*((5.76-bp)/2+bp)
    fanout=math.floor(5.76/bp)  # other half of11.52 is positive wire reserve
    def tree(seats):
        levels=[seats]
        while levels[-1]>1:levels.append(math.ceil(levels[-1]/fanout))
        return dict(levels_leaf_to_root=levels,cells=sum(levels),depth=len(levels))
    def delay(depth):return cq+initial+first+(depth-1)*later+depth*wire+go+setup+60+25
    permitted_depth=1
    while delay(permitted_depth+1)<=T:permitted_depth+=1
    max_leaf_sites=fanout**(permitted_depth-1)
    groups=math.ceil(2048/max_leaf_sites)
    group_sites=[2048//groups+(i<2048%groups) for i in range(groups)]
    fields={};shared_buffers=0
    for name,qp in actual['cases']['q'].items():
        if name.startswith('cfg_'):continue  # real per-pair loader, not shared activation
        bf=actual['cases']['bfcolumn'][name];live=[]
        for i,(a,z) in enumerate(zip(qp['bits'],bf['bits'])):
            qlive=max(a['SS_cap_fF'],a['FF_cap_fF'])>0;blive=max(z['SS_cap_fF'],z['FF_cap_fF'])>0
            if max(a['SS_cap_fF'],a['FF_cap_fF'],z['SS_cap_fF'],z['FF_cap_fF'])>5.76:raise ValueError('shared leaf must price a larger leaf driver')
            n=(1686 if qlive else 0)+(362 if blive else 0)
            if n:
                # Each group owns a positive complete tree, including root.
                # BF-only bits overcharge as all sites: no active-site mask credit.
                copies=[tree(v) for v in group_sites];cells=sum(t['cells'] for t in copies)
                shared_buffers+=cells
                live.append(dict(index=i,actual_Q_pin_fF=max(a['SS_cap_fF'],a['FF_cap_fF']),actual_BF_pin_fF=max(z['SS_cap_fF'],z['FF_cap_fF']),source_live_sites=n,charged_sites=2048,tree_cells=cells))
        fields[name]=dict(declared_bits=qp['width'],live_bits=len(live),bit_loads=live)
    leaf_needs8=[dict(case=k,port=n,index=i,actual_pin_fF=max(a['SS_cap_fF'],a['FF_cap_fF'])) for k,v in actual['cases'].items() for n,p in v.items() for i,a in enumerate(p['bits']) if n.startswith('cfg_') and max(a['SS_cap_fF'],a['FF_cap_fF'])>11.52]
    # Clock segment must propagate slew including wire, not just gate LUT.
    clock_wire_cap=11.52;clock_pin_cap=23.04;L=clock_wire_cap/C
    clock_wire=R*L*(clock_wire_cap/2+clock_pin_cap)
    clock_cell_slew=max(S.lut(ss[b],k,320,46.08) for k in ('rise_transition','fall_transition'))
    conservative_slew=clock_cell_slew+2.2*clock_wire
    if conservative_slew>320:raise ValueError('positive clock segment violates slew envelope')
    lef=gzip.decompress(raw['cells.lef.gz']).decode()
    def area(master):
        z=re.search(r'^MACRO '+master+r'\s*$(.*?)^END '+master+r'\s*$',lef,re.M|re.S)[1]
        w,h=map(float,re.search(r'SIZE ([\d.]+) BY ([\d.]+)',z).groups());return w*h
    clocks={}
    for kind,v in profiles['cases'].items():
        width=510.84 if kind=='q' else 1002.89;height=157.68
        columns=math.ceil((width-276.48)/(L/2));rows=math.ceil(height/(L/2));anchors=columns*rows
        nets=[]
        for net,p in v['ff'].items():
            cp=max(p['pin_cap_fF'],v['ss'][net]['pin_cap_fF']);t=S.tree_count(cp,bp,clock_pin_cap)
            a=1 if p['sinks']==1 else anchors+(4 if p['source_ICG'].endswith('g_leaf[0].u_cg.u_icg') else 0)
            nets.append(dict(net=net,owner=p['source_ICG'],source_pin_fF=cp,tree=t,distribution_anchors=a))
        depth=max(len(x['tree']['levels']) for x in nets if x['owner']!='root')
        total=sum(x['tree']['cells']+x['distribution_anchors']+(depth-len(x['tree']['levels']) if x['owner']!='root' else 0) for x in nets)
        old=sum(p['BUF4_capacitance_only']['cell_count'] for p in v['ff'].values())
        clocks[kind]=dict(nets=nets,BUF_total=total,old_capacitance_only_BUF=old,incremental_cell_um2=(total-old)*area(b),compute_anchor_grid=[columns,rows],anchor_tile_max_L1_um=L,macro_capture_anchors_extra=4,actual_anchor_placement=False,old_cell_floor_subtracted_once=True)
    copies=(groups-1)*1632
    return dict(actual_boundary_pin_source={k:actual[k] for k in ('commit','path','raw_sha256')},actual_full_declared_input_loads=fields,local_CFG_requires_BUF8=leaf_needs8,
        shared_broadcast=dict(full_source_bus_bits=1632,nominal_sites_per_shard=2048,finite_BUFFER_branch_fanout=fanout,unreplicated_tree=tree(2048),unreplicated_GO_setup_upper_ps=delay(tree(2048)['depth']),permitted_GO_tree_depth=permitted_depth,source_endpoint_group_count=groups,source_endpoint_group_sizes=group_sites,selected_GO_setup_upper_ps=delay(max(tree(x)['depth'] for x in group_sites)),period_ps=T,SS_setup_uncertainty_ps=60,FF_hold_uncertainty_ps=25,skew_reservation_ps=25,source_final_BST_register_replication_proposal=True,added_BST_register_bits_per_shard=copies,added_source_edges=0,replication_after_same_previous_BST_edge_must_be_proven=True,source_clock_reset_data_modes_all_aligned=True,actual_shared_tree_BUFFER_cells_per_shard=shared_buffers,positive_shared_tree_cell_floor_at50pct_mm2=shared_buffers*area(b)*2/1e6,register_replica_floor_at50pct_mm2=copies*area(d)*2/1e6,source_GO_AND2_positive_cell_floor_um2=2048*area(gate['master']),source_payload_not_reordered=True,implementation_admitted=False),
        clock=dict(root_and_eight_ICG_profiles=clocks,maximum_pin_cap_fF=clock_pin_cap,wire_cap_fF=clock_wire_cap,total_cap_fF=clock_pin_cap+clock_wire_cap,maximum_segment_um=L,wire_Elmore_ps=clock_wire,SS_cell_slew_upper_ps=clock_cell_slew,SS_cell_plus_2p2_wire_slew_ps=conservative_slew,slew_constraint_ps=320,SS_macro_min_high_low_pulse_ps=284.741,source_master_clock_min_period_ps=711.852,minimum_pulse_and_25ps_skew_are_enforced_constraints_not_installed_CTS=True,grid_scope='retained q151.20um/BF157.68um; conservative5-row grid from157.68 fits either height; compute plane x>=276.48, square pitchL/2. Grid anchors are NOT legal cell sites or PG containment.',STA_wire_admission=False),
        scope='finite constructive analytical domain only; overloaded enable cause resolved by b8; repaired slew remains unqualified. Source-matched grid anchor/corridor/PG legality and FFhold must be demonstrated before context PR. Extra final-BST copies are PROPOSED, not an existing provider and not a zero-cost latency claim.',full_context_PR_admitted=False)

def whole_join(parent):
    """Disjoint conservative additions; no containment or extracted fit credit."""
    import gzip, math
    origins=json.loads((BASE/'inputs/new_owner_origins.json').read_text())
    owner={}
    for n,r in origins.items():
        data=(BASE/'inputs'/n).read_bytes()
        if hashlib.sha256(data).hexdigest()!=r['copy_sha256']:raise ValueError('owner input changed: '+n)
        plain=gzip.decompress(data) if n.endswith('.gz') else data
        if hashlib.sha256(plain if n.endswith('.json.gz') else data).hexdigest()!=r['original_sha256']:raise ValueError('owner original mismatch: '+n)
        if n.endswith('.json') or n.endswith('.json.gz'):owner[n]=json.loads(plain)
    e=owner['enable_distribution.json.gz'];z=owner['selector_authoritative.json'];historical=owner['historical_enable_6ed.json.gz']
    if e['candidate']!='DS4096-TP4-S58-PAR2-NP2048':raise ValueError('different candidate')
    raw,_=S.load();prior=json.loads(raw['prior_reticle.json'])
    clocks=parent['clock']['root_and_eight_ICG_profiles'];shared=parent['shared_broadcast']
    enable=[]
    for k,n in [('q',1686),('bfcolumn',362)]:
        c=e['cases'][k]
        if c['added_physical_FF']!=8 or c['added_capture_latency_cycles']!=0:raise ValueError('different enable state/edge')
        if c['placement_cell_collisions'] or c['placement_macro_body_collisions'] or c['placement_source_WAKExICG_collisions']:raise ValueError('owner placement collision')
        enable.append(dict(case=k,instances_per_shard=n,added_enable_FF_per_element=8,existing_WAKE_FF_per_element=8,existing_WAKE_recharged=False,core_um2_per_element=c['conservative_50pct_core_reservation_um2'],reviewed_previous_um2=38.7828,delta_vs_previous_um2=c['conservative_50pct_core_reservation_um2']-38.7828,clone_CLK_fF=c['clone_clock_pin_debit_SS_FF_fF'],clone_RESETN_fF=c['clone_reset_pin_debit_SS_FF_fF'],minimum_SS_screen_remaining_ps=c['minimum_SS_remaining_ps'],D_FF_hold_screen_margins_ps=[a['SS_FF_complete_D_path']['ff']['FF_hold_margin_ps'] for a in c['proposed_D_distribution']],source_snapshot_sha256=origins['enable_distribution.json.gz']['original_sha256']))
    # The new 8 FF clocks have a distinct leaf: no free use of the WAKE tree.
    lef=gzip.decompress(raw['cells.lef.gz']).decode()
    def cellarea(master):
        block=re.search(r'^MACRO '+master+r'\s*$(.*?)^END '+master+r'\s*$',lef,re.M|re.S)[1]
        w,h=map(float,re.search(r'SIZE ([\d.]+) BY ([\d.]+)',block).groups());return w*h
    buf_area=cellarea('BUFx4_ASAP7_75t_R');bf_cfg_buf8_area=cellarea('BUFx8_ASAP7_75t_R')
    clone_CLK=sum(x['instances_per_shard']*max(x['clone_CLK_fF'].values()) for x in enable)
    clone_RST=sum(x['instances_per_shard']*max(x['clone_RESETN_fF'].values()) for x in enable)
    clone_clock_leaf=2048
    # One independent reset leaf per element, full finite 9-ary upstream tree.
    levels=[2048]
    while levels[-1]>1:levels.append(math.ceil(levels[-1]/shared['finite_BUFFER_branch_fanout']))
    reset_cells=sum(levels)
    additions=[
        dict(id='selector_source_correct_station',mm2=z['cost']['station_cell_reservation_mm2_at50pct'],basis='replace old102-cycle station; station-free predecessor; includes48007 pin-only clock BUF, global spatial clock/PG still unpriced'),
        dict(id='shared_broadcast_BUF',mm2=shared['positive_shared_tree_cell_floor_at50pct_mm2'],basis='3726496 BUF/shard; no local3-buffer substitution'),
        dict(id='same_BST_replica_register_floor',mm2=shared['register_replica_floor_at50pct_mm2'],basis='3264bits; generic FF floor only; reset/polarity/hold source circuit remains required'),
        dict(id='enable_source_repair',mm2=sum(x['instances_per_shard']*x['core_um2_per_element'] for x in enable)/1e6,basis='8 new FF distinct from8 inheritedWAKE; two D hold networks; existing macro/capture area credit0'),
        dict(id='finite_spatial_element_clock_increment',mm2=sum((1686 if k=='q' else 362)*v['incremental_cell_um2']*2/1e6 for k,v in clocks.items()),basis='901/2724 BUF minus inherited84/261 once; positive modeled grid not legal site proof'),
        dict(id='enable_clone_clock_leaf',mm2=clone_clock_leaf*buf_area*2/1e6,basis='one separate positive leaf per8FF group; CLK pins4.100648fF <23.04; upstream root/capture waveform unqualified'),
        dict(id='enable_clone_reset_tree',mm2=reset_cells*buf_area*2/1e6,basis='reset pin3.211636fF <5.76 plus positive wire5.76; complete9-ary tree; actual launch/recovery/removal unqualified'),
        dict(id='local_BF_CFG_large_leaf',mm2=362*bf_cfg_buf8_area*2/1e6,basis='source BF cfg_a0 pin11.549872; BUF8 positive LEF cell floor; held loader semantics not changed')]
    # The q6.48um extension is a modeled outline reservation, not an actual LEF.
    extension=510.84*6.48*1686/1e6
    # Retained q151.20 already has a6.48um bottom strip144.72..151.20.
    # A second extension is a policy counterfactual, not selected or charged.

    baseline=prior['area']['screen_with_corridor_mm2'];total=baseline+sum(x['mm2'] for x in additions)
    return dict(schema='DS_S58_PAR2_SELECTED_CALLER_WHOLE_JOIN_V1',owner_pins=origins,baseline_station_free_mm2=baseline,baseline_scope='inherited completeq/BF frames, selector1.68242, WAKE, conservative fixedservice/return/config/corridors; historical model screen, not actual fit',additions=additions,screen_mm2=total,reticle_mm2=858,screen_margin_mm2=858-total,q_second_extension_counterfactual_mm2=extension,q_selected_outline_um=[510.84,151.20],BF_selected_outline_um=[1002.89,157.68],q_existing_bottom_strip_um=[144.72,151.20],dimension_limit_um=[26000,33000],actual_packing_PASS=False,no_double_count=dict(selector_core_1p68242_once=True,old102cycle_station_not_added=True,BF_growth_once=True,WAKE8_once=True,all_compiled2048_sites_charged=True,ROM_ECC_required=False),enable=enable,historical_6ed_enable=dict(preserved=True,core_um2_per_element=historical['cases']['q']['conservative_50pct_core_reservation_um2'],D_FF_hold_screen_margins_ps=[a['SS_FF_complete_D_path']['ff']['FF_hold_margin_ps'] for a in historical['cases']['q']['proposed_D_distribution']],snapshot_sha256=origins['historical_enable_6ed.json.gz']['original_sha256'],new_repair_delta_core_mm2_per_shard=(e['cases']['q']['conservative_50pct_core_reservation_um2']-historical['cases']['q']['conservative_50pct_core_reservation_um2'])*2048/1e6),finite_clock_reset_extra=dict(clone_CLK_pin_sum_fF=clone_CLK,clone_RESETN_pin_sum_fF=clone_RST,clock_leaf_BUF_cells=clone_clock_leaf,reset_BUF_levels_leaf_to_root=levels,reset_BUF_cells=reset_cells,reset_deassert_recovery_removal_unqualified=True,whole_root_capacity_and_actual_skew_unqualified=True),latency=dict(selector_station_cycles_per_call=226,nine_station_cycles=2034,selector_service_cycles_per_call=142,nine_combined_cycles=3312,nine_combined_ns_1p2GHz=2760,conditional_six_verify_positions_ns=16560,drafter_commit_rollback_not_covered=True,enable_and_caller_added_sampling_edges=0,zero_edge_same_BST_replica_proof_pending=True,whole_token_no_loss_proven=False),slew_diagnosis=dict(cause_resolved=True,cause='Graph worst incoming enable arc; data report_dcalc alone is not graph slew;1088sinks392.441fF overloadedNOR',unbuffered_failed_evidence_preserved=True,actual_repaired_SSFF=False),frontend=dict(selected_source_manifest='replace four originals with source_overrides; flags1 at everyfield/pair/element; defaults0',static_source_gate=True,actual_elaboration=False,selected_frontend_admitted=True,admitted_scope='source configuration elaboration only, no engine alteration or physical build',full_context_PR_admitted=False),remaining=['same-edge BST resettable1632bit replication and QN restoration full circuit/D/hold cost and proof','exact source c_v/c_a/c_d reset/held loader and cfgGO driver max/min with finite full shared branch wire placement','enable clone CLK/reset root union, actual D min/max fanout and every strip PG/via/pin escape','selector226 circuit actual cell sites/global clock/PG/reset; pin-only48007 clockBUF cannot reach full die','source parent return/output loads and clock skew/pulse/recovery/removal; registered fullconeSS60/FF25 closure'],old_failures_unchanged=True,build_admitted=False)

def build():
    records = json.loads((BASE/'inputs/origins.json').read_text())
    old = {}
    for name,r in records.items():
        p=BASE/'inputs'/name
        if digest(p)!=r['sha256'] or digest(ROOT/r['path'])!=r['sha256']:
            raise ValueError('pinned original source changed')
        old[name]=p.read_text()
    field=ROOT/'rtl/v41die/ot_v41_field_w17w10_rne_wake_prepare.sv'
    top=ROOT/'rtl/v41die/ot_v41_fieldtop_w17w10_rne_wake_prepare.sv'
    if field.read_text()!=S.propose_field(old['field.sv']):
        raise ValueError('field companion is not exact parameter-only proposal')
    declarations=''.join('    parameter integer '+f+' = 0,\n' for f in S.FLAGS)
    forwards=' '.join('.'+f+'('+f+'),' for f in S.FLAGS)
    if top.read_text().replace(declarations,'').replace(forwards+' ','')!=old['fieldtop.sv']:
        raise ValueError('fieldtop companion changes more than parameter forwarding')
    for text in (top.read_text(),field.read_text()):
        for f in S.FLAGS:
            if text.count('parameter integer '+f+' = 0,')!=1 or text.count('.'+f+'('+f+')')!=1:
                raise ValueError('missing/duplicate declared named binding')
    pair=ROOT/'rtl/v41die/ot_v41_pair_w17w10_rne_wake_prepare.sv'
    elem=ROOT/'rtl/v41rom/ot_v41_rom_elem_w10_rne_wake_prepare.sv'
    raw,origins=S.load()
    for p,n in ((pair,'ot_v41_pair_w17w10_rne_wake_prepare.sv'),(elem,'selected_element.sv')):
        if p.read_bytes()!=raw[n]:raise ValueError('prepared child no longer matches measured source')
    for f in S.FLAGS:
        if '.'+f+'('+f+')' not in pair.read_text():raise ValueError('pair to element gap')
    selected={f:1 for f in S.FLAGS}
    # Literal generate index and BF predicate preserved; model checks every
    # compiled site, not a smaller template or an active-mask charge.
    global_bf={i*4096//724 for i in range(724)}
    local_bf={i*2048//362 for i in range(362)}
    sites=[dict(shard=s,local_site=g,global_site=s*2048+g,BF16=int(g in local_bf),selected_element_parameters=selected) for s in range(2) for g in range(2048)]
    if {x['global_site'] for x in sites if x['BF16']}!=global_bf:raise ValueError('BF mask changed across PAR2')
    if not re.search(r'for \(g = 0; g < NP; g = g \+ 1\)',field.read_text()):raise ValueError('literal full compiled field generate changed')
    return dict(schema='opentallas.dsrom.selected-parent-caller.v1',candidate='DS4096-TP4-S58-PAR2-NP2048',original_sourcepins=records,
        source_overrides=[dict(original='rtl/v41die/ot_v41_fieldtop_w17w10.sv',selected=str(top.relative_to(ROOT)),sha256=digest(top)),dict(original='rtl/v41die/ot_v41_field_w17w10.sv',selected=str(field.relative_to(ROOT)),sha256=digest(field)),dict(original='rtl/v41die/ot_v41_pair_w17w10.sv',selected=str(pair.relative_to(ROOT)),sha256=digest(pair)),dict(original='rtl/v41rom/ot_v41_rom_elem_w10.sv',selected=str(elem.relative_to(ROOT)),sha256=digest(elem))],
        selection_rule='REPLACE original source filenames in selected source manifest; never read both definitions of same module',source_configuration=dict(default_flags={f:0 for f in S.FLAGS},selected_flags=selected,selected_field_parameters=dict(NP=2048,NBF=362,R=64,PHW=10,FAST=1,PP=1,BP=0),full_compiled_sites=4096,q_sites=3372,BF_DUAL_sites=724,physical_weight_macros=16384,all_site_forwarding_static_gate=True,upstream_fieldtop_and_direct_field_supported=True,RT_CUT_host_must_select_same_three_template_values=True,fieldtop_VM_is_equivalence_model_not_physical_provider=True),
        exact_source_gate=dict(parameter_only_inverse=True,originals_byteidentical=True,pair_and_element_match_measured_source=True,all_other_ports_clock_payload_arithmetic_reduction_logic_unchanged=True,elaborated=False,numerical_or_context_qualification=False),
        cost=dict(additional_cycles_vs_measured_selected_elements=0,additional_cells_vs_measured_selected_elements=0,changed_from_historical_default0_cannot_inherit_historical_area_or_timing=True,no_WAKE_or_RNE_recharge=True),
        finite_parent_construction=finite_parent(),whole_reticle_join=whole_join(finite_parent()),physical_admission=False,remaining=['Selected manifest and flags must be consumed by actual physical/context frontend; this gate is static source binding','final BST same-edge replica proof and numeric loader/reset/clock/return constraints; actual selector PG/station/endpoint geometry','overloaded enable cause resolved; actual repair/wire/clock/reset/FFhold remain unqualified; no new capture edge'],generator_sha256=digest(Path(__file__))),sites

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--reemit-boundary',type=Path);a=p.parse_args()
    if a.reemit_boundary:
        result=extract_boundary(a.reemit_boundary.read_bytes())
        with a.out.open('x') as f:f.write(json.dumps(result,indent=2,sort_keys=True)+'\n')
    else:
        a.out.mkdir(parents=True,exist_ok=False)
        model,sites=build();(a.out/'model.json').write_text(json.dumps(model,indent=2,sort_keys=True)+'\n')
        import gzip
        (a.out/'compiled_site_parameters.jsonl.gz').write_bytes(gzip.compress(''.join(json.dumps(s,sort_keys=True)+'\n' for s in sites).encode(),mtime=0))
