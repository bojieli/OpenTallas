"""Finite selected-caller branch geometry and accepted I66 physical obligations.
No hardware execution; clock stations are proposed sites, not extracted CTS.
"""
import argparse, gzip, hashlib, json, math, re
from collections import Counter
from pathlib import Path
import dsrom_selected_parent_caller as C
import dsrom_selector_station_parent_binding as S
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'results/uarch/dsrom_selected_caller_branch_edges_20261002'

def read_inputs():
    origins=json.loads((BASE/'inputs/origins.json').read_text());data={}
    for n,r in origins.items():
        raw=(BASE/'inputs'/n).read_bytes()
        if hashlib.sha256(raw).hexdigest()!=r['copy_sha256']:raise ValueError('input hash mismatch: '+n)
        plain=gzip.decompress(raw) if n.endswith('.gz') else raw
        if not r.get('derived') and hashlib.sha256(plain).hexdigest()!=r['original_sha256']:raise ValueError('original bytes differ')
        data[n]=json.loads(plain) if '.json' in n else plain.decode()
    return data,origins

def rect_overlap(a,b):return min(a[2],b[2])>max(a[0],b[0]) and min(a[3],b[3])>max(a[1],b[1])
def point(rect):return [(rect[0]+rect[2])/2,(rect[1]+rect[3])/2]
def L1(a,b):return abs(a[0]-b[0])+abs(a[1]-b[1])
def LEF_pin(templates,cell,pin):
    p=next(p for p in templates[cell['master']]['pins'] if p['name']==pin)
    box=next(r['bbox_DBU'] for r in p['rectangles'] if r['layer']=='M1')
    h=templates[cell['master']]['size_DBU'][1]
    if cell['orientation']=='MX':box=[box[0],h-box[3],box[2],h-box[1]]
    return [v+cell['bbox_DBU'][i%2] for i,v in enumerate(box)]

def locate_buffer(want,existing,frame):
    # Candidate legal-row body search. Electrical PG/pin access is NOT inferred.
    x=round(want[0]/54)*54;y=round((want[1]-135)/270)*270
    candidates=sorted(((abs(dx)+abs(dy),x+dx,y+dy) for dy in range(-5400,5401,270) for dx in range(-540,541,54)))
    for _,x,y in candidates:
        box=[x,y,x+378,y+270]
        if box[0]<0 or box[1]<0 or box[2]>frame[2] or box[3]>frame[3]:continue
        if not any(rect_overlap(box,r) for r in existing):return box
    raise ValueError('no local buffer body site; do not grant free area')

def interpolate_polyline(poly,distance):
    for a,b in zip(poly,poly[1:]):
        length=L1(a,b)
        if distance<=length:
            if length==0:return a
            return [a[i]+(b[i]-a[i])*distance/length for i in (0,1)]
        distance-=length
    return poly[-1]

def hold_wire_geometry(source):
    """Same lengths and source RC; preferred-M3 construction within one repair."""
    h=source['hold_wire_construction']
    if h['first_length_um']!=18.432 or h['second_length_um']!=5.4:raise ValueError('different hold repair')
    # M3 source pitch36/width18/spacing18. VIA23 M3 y-enclosure14 +18spacing+9halfwire.
    guard=41
    # A5-pass horizontal snake with108nm row separation cannot clear270nm PGrail crossings.
    best_phase_clearance=max(min(min((y+k*108)%270,270-(y+k*108)%270) for k in range(5)) for y in range(270))
    poly=[[279009,72009]]
    for k in range(5):
        x=279009+k*108;y=75609 if k%2==0 else 72009
        poly.append([x,y])
        if k<4:poly.append([x+108,y])
    second=[[279801,75801],[279801,81201]]
    lengths=[sum(L1(a,b) for a,b in zip(z,z[1:]))/1000 for z in (poly,second)]
    if lengths!=[18.432,5.4]:raise ValueError('wire load disappeared')
    # Nearest source M5 power columns, pitch2700/paired spacing192/offset300.
    columns=[300+n*2700+offset for n in range(200) for offset in (0,192)]
    xs=[v[0] for v in poly+second]
    minimum_x_clearance=min(abs(x-c) for x in xs for c in columns)
    if minimum_x_clearance<=guard:raise ValueError('held wire conflicts with source PGvia column')
    if any((x-9)%36 for x in xs):raise ValueError('off source M3 track phase')
    return dict(source_first_horizontal_pattern_max_phase_clearance_DBU=best_phase_clearance,source_default_PGvia_required_clearance_DBU=guard,horizontal_pattern_not_legal_under_full_source_default_array=(best_phase_clearance<guard),selected_same_length_preferred_M3_polylines_DBU=[poly,second],lengths_um=lengths,minimum_M5via_column_clearance_DBU=minimum_x_clearance,source_M3_track_phase_DBU=9,pitch_DBU=36,width_DBU=18,source_M2_PGrail_pitch_DBU=270,source_M5_PGpair_pitch_DBU=2700,source_M5_PGpair_spacing_DBU=192,source_RC_unchanged=True,hold_BUF_count_unchanged=2,additional_cell_debit=0,already_charged_in_current_enable40p06584=True,BUF_pin_VIA12_23_stubs_must_be_added_to_max_and_min_load=True,source_driver_placement_and_other_fanout_still_bound_by_owner=True,default_arrays_are_source_construction_not_installed_PDN=True,physical_wire_qualified=False)

def same_BST_model(inputs,caller):
    delay=inputs['delay.sv'];spine=inputs['spine.sv']
    if 'ot_hdc_delay #(.W(BW), .D(BST), .RESET(1)) u_bst' not in spine:raise ValueError('source BST reset binding changed')
    for text in ["always @(posedge clk or negedge rst_n)","if (!rst_n) line <= {(W*D){1'b0}};","else line <= {line[W*(D-1)-1:0], d};","assign q = line[W*D-1 -: W];"]:
        if text not in delay:raise ValueError('different literal delay recurrence')
    # Bitwise transition theorem: after common reset, source final stage and every
    # same-edge copy consume identical pre-edge stage16 bit, includingX/Z.
    states=['0','1','X','Z'];checks=0
    for previous in states:
        for incoming in states:
            for rst in states:
                expected='0' if rst=='0' else incoming
                for _ in range(3):
                    copied='0' if rst=='0' else incoming
                    if copied!=expected:raise ValueError('replica transition differs')
                    checks+=1
    raw,_=S.load();seq=json.loads(raw['SS_driver_cells.json'])['cell_bodies'];lib=gzip.decompress(raw['invbuf_ss.lib.gz']).decode()
    def cell(name):return S.block(lib,re.search(r'\bcell\s*\('+name+r'\)\s*\{',lib).start())
    inv=cell('INVx1_ASAP7_75t_R');buf=seq['BUFx4_ASAP7_75t_R'];a=seq['DFFASRHQNx1_ASAP7_75t_R'];d=seq['DFFHQNx1_ASAP7_75t_R']
    cq=max(S.lut(a,k,320,1.44) for k in ('cell_rise','cell_fall'));cq0=max(S.lut(d,k,320,5.76) for k in ('cell_rise','cell_fall'))
    inv_delay=max(S.lut(inv,k,80,5.76) for k in ('cell_rise','cell_fall'))
    inv_slew=max(S.lut(inv,k,80,5.76) for k in ('rise_transition','fall_transition'))
    wire_initial=.031287*((5.76-.581966)/.178475)*((5.76-.581966)/2+.581966)
    wire_regular=.031287*((11.52-.581966)/.178475)*((11.52-.581966)/2+.581966)+2*.0172*11.52
    local=.031287*((1.44-S.cap(inv,'A'))/.178475)*1.44
    depth=caller['finite_parent_construction']['shared_broadcast']['permitted_GO_tree_depth']
    slew=inv_slew+2.2*wire_initial;delays=[];input_envelopes=[]
    for k in range(depth):
        domain=next(x for x in [5,10,20,40,80,160,320] if x>=slew)
        cap=11.52;delays.append(max(S.lut(buf,z,domain,cap) for z in ('cell_rise','cell_fall')));input_envelopes.append(domain)
        slew=max(S.lut(buf,z,domain,cap) for z in ('rise_transition','fall_transition'))+2.2*wire_regular
    go=json.loads((C.BASE/'inputs/GO_gate_cell.json').read_text())['cell_body']
    domain=next(x for x in [5,10,20,40,80,160,320] if x>=slew)
    go_delay=max(S.lut(go,z,domain,5.76) for z in ('cell_rise','cell_fall'))
    # Re-use original period/uncertainty/skew; no extra edge selected.
    total=cq+local+inv_delay+wire_initial+sum(delays)+depth*wire_regular+go_delay+S.constraint(d,'setup_rising')+60+25
    bits=3264
    additions=dict(reset_ASR_vs_generic_FF_mm2=bits*(.37908-.2916)*2/1e6,QN_restoring_INV_mm2=bits*.04374*2/1e6,SETN1_local_TIEHI_mm2=bits*.04374*2/1e6,three_HB_per_copy_hold_reservation_mm2=bits*3*.0729*2/1e6)
    # Source reset and clock pin obligations for the2 additional copies.
    corner=json.loads(raw['FF_driver_cells.json'])['cell_bodies']['DFFASRHQNx1_ASAP7_75t_R']
    def pcap(body,pin):
        part=S.block(body,re.search(r'\bpin\s*\('+pin+r'\)\s*\{',body).start())
        return max(float(x) for x in re.findall(r'\b(?:capacitance|rise_capacitance|fall_capacitance)\s*:\s*([\d.eE+-]+)',part))
    pin_counts={}
    for pin,budget in [('CLK',23.04),('RESETN',5.76)]:
        cap=bits*max(pcap(a,pin),pcap(corner,pin));levels=[math.ceil(cap/budget)]
        while levels[-1]>1:levels.append(math.ceil(levels[-1]/9))
        pin_counts[pin]=dict(total_extra_pin_fF=cap,BUF_levels_leaf_to_root=levels,BUF_cells=sum(levels),wire_cap_reservation_fF=5.76,placement_and_parent_union_unknown=True)
    additions['replica_CLK_RESET_pin_tree_floor_mm2']=sum(x['BUF_cells'] for x in pin_counts.values())*.10206*2/1e6
    return dict(replica_CLK_RESET_pin_floor=pin_counts,literal_RESET1_source_gate=True,source_BST=17,source_width=1632,new_copies=2,additional_register_edges=0,bitwise_fourstate_induction_cases=checks,proof_scope='same clock/reset/data and initialized commonreset; source transition proof only, no implemented RTL or skew/extraction proof',stale_or_gated_clock_copy_not_equivalent=True,source_QN_must_restore=True,all3264_added_bits_require_reset_not_genericHQ=True,positive_source_circuit_additions_vs_b328_generic_floor=additions,total_additional_cell_floor_mm2=sum(additions.values()),hold_reservation_is_not_FFclosure=True,HB1p2p3_minload_and_slew_domains_must_be_enforced=True,reviewed_generic_GO_upper_ps=caller['finite_parent_construction']['shared_broadcast']['selected_GO_setup_upper_ps'],source_ASR_CQ_ps=cq,source_INV_delay_ps=inv_delay,source_INV_output_slew_ps=inv_slew,recursive_BUF_input_domains_ps=input_envelopes,final_GO_input_domain_ps=domain,recursive_source_correct_GO_upper_ps=total,period_ps=1000/1.2,recursive_LUT_RC_screen_PASS=total<=1000/1.2,screen_failure_not_actual_STA_or_architectural_impossibility=True,no_new_capture_edge_or_variant_selected=True,actual_full_source_cone_required=True,tail_AND_and_HQ_destination_setup_retained_as_reviewed_floor_not_full_GOact_cone=True)

def build():
    inputs,origins=read_inputs();caller,_=C.build();bst=same_BST_model(inputs,caller);j=caller['whole_reticle_join'];p=caller['finite_parent_construction'];i=inputs['I66.json'];cuts=inputs['local_cuts.json.gz']
    if i['candidate']!=caller['candidate'] or cuts['candidate']!=i['candidate']:raise ValueError('candidate mismatch')
    flow=inputs['accepted_flow.json']
    if flow['raw_journal_sha256']!=i['runtime_journal_raw_sha256']:raise ValueError('wrong actual journal')
    enable=inputs['enable8d6.json.gz']
    enable_revision_delta=(enable['cases']['q']['conservative_50pct_core_reservation_um2']-39.59928)*2048/1e6
    raw,_=S.load();macro=json.loads(raw['prior_reticle.json'])['q']['macro_clock_reach']
    macro_boxes=[x['macro']['bbox_DBU'] for x in macro]
    max_wire=p['clock']['maximum_segment_um']*1000
    result={};stations=[]
    for kind,c in enable['cases'].items():
        template=enable['physical_master_templates'];g=cuts['cases'][kind]
        icg=next(x for x in g['source_clock_cell_slots'] if x['role']=='sourceICG' and x['leaf']==0)
        # Exact retained LEF GCLK rectangle from source master, not a center-of-cut pin.
        lef=gzip.decompress(raw['cells.lef.gz']).decode()
        master=re.search(r'^MACRO '+icg['master']+r'\s*$(.*?)^END '+icg['master']+r'\s*$',lef,re.M|re.S)[1]
        pin=re.search(r'  PIN GCLK\n(.*?)  END GCLK',master,re.S)[1]
        box=[round(float(x)*1000) for x in re.search(r'RECT ([\d.]+) ([\d.]+) ([\d.]+) ([\d.]+)',pin).groups()]
        clk_origin=point([v+icg['bbox_DBU'][k%2] for k,v in enumerate(box)])
        replicas=[x for x in c['placements'] if x['role']=='control_state_replica']
        if len(replicas)!=8:raise ValueError('lost enable FF')
        nets=[]
        for cell in replicas:
            for name in ['CLK']+(['RESETN'] if cell['master']=='DFFASRHQNx1_ASAP7_75t_R' else []):
                target=point(LEF_pin(template,cell,name));xcol=137421 if target[0]<200000 else 274797
                # Same registered owner; reset ingress at this anchor is proposed, not an actual parent pin.
                origin=clk_origin if name=='CLK' else [278640,1788]
                # Reset uses a DISTINCT proposed boundary anchor, not the GCLK pin.
                poly=[origin,[xcol,origin[1]],[xcol,target[1]],target]
                nets.append(dict(instance=cell['instance'],pin=name,source_net='leaf_clk[0]' if name=='CLK' else 'rst_n',source_owner=icg['actual_instance'] if name=='CLK' else 'parent rst_n; physical ingress UNBOUND',endpoint_pin_bbox_DBU=LEF_pin(template,cell,name),endpoint_orientation=cell['orientation'],polyline_DBU=poly,L1_wire_um=sum(L1(a,b) for a,b in zip(poly,poly[1:]))/1000))
        # All clock paths get the same number of BUF cells. This does not prove skew of existing siblings.
        stages=max(math.ceil(n['L1_wire_um']*1000/(max_wire*.8)) for n in nets)
        occupied=[x['bbox_DBU'] for x in c['placements']]+macro_boxes+[x['bbox_DBU'] for x in g['source_clock_cell_slots']]
        for n in nets:
            placed=[];total=n['L1_wire_um']*1000
            for k in range(stages):
                want=interpolate_polyline(n['polyline_DBU'],total*(k+1)/(stages+1))
                b=locate_buffer(want,occupied,g['outline_DBU']);occupied.append(b)
                r=dict(case=kind,net_owner=n['source_owner'],sink=n['instance']+'.'+n['pin'],stage=k,bbox_DBU=b,master='BUFx4_ASAP7_75t_R',orientation='R0',body_clear_of_archived_primitives_macro_bodies_and_WAKE_ICG=True,PG_pin_via_access_proven=False)
                placed.append(r);stations.append(r)
            chain=[n['polyline_DBU'][0]]+[point(x['bbox_DBU']) for x in placed]+[n['polyline_DBU'][-1]]
            # Proposed routing preserves the original column detour between every placed anchor.
            lengths=[]
            for a,b in zip(chain,chain[1:]):lengths.append(L1(a,b)/1000)
            if max(lengths)*1000>max_wire:raise ValueError('station segment exceeds priced wire domain')
            n.update(BUF_cells=stages,BUF_bbox_DBU=[x['bbox_DBU'] for x in placed],segment_L1_um=lengths,maximum_segment_um=max(lengths),route_polyline_between_stations_not_extracted=True)
        union=c['clock_reset_full_source_union']
        for corner in ('ss','ff'):
            prof=C.finite_parent()['clock']['root_and_eight_ICG_profiles'][kind]['nets']
            leaf=next(x for x in prof if x['owner'].endswith('g_leaf[0].u_cg.u_icg'))
            oldpins=json.loads((C.BASE/'inputs/clock_pin_profiles.json').read_text())['cases'][kind][corner][union[corner]['existing_leaf0_net_id']]
            if abs(oldpins['pin_cap_fF']-union[corner]['existing_leaf0_pin_cap_fF'])>1e-6:raise ValueError('leaf0 source load mismatch')
            if union[corner]['new_leaf0_sinks']!=oldpins['sinks']+8:raise ValueError('clock clone union lost source sinks')
        if c['source_PG_rail_projection_failures']:raise ValueError('source cell PG projection failed')
        reset_levels=[math.ceil(max(v['existing_reset_pin_cap_fF'] for v in union.values())/5.76)]
        while reset_levels[-1]>1:reset_levels.append(math.ceil(reset_levels[-1]/9))
        result[kind]=dict(full_existing_reset_positive_BUF_levels=reset_levels,full_existing_reset_positive_BUF=sum(reset_levels),full_existing_reset_scope='original reset pins only; clone20 stationBUF priced separately, globalpair tree inherited once',committed_enable_um2=c['conservative_50pct_core_reservation_um2'],clock_reset_full_source_union=union,existing_RST_full_source_pin_cap_fF=max(v['existing_reset_pin_cap_fF'] for v in union.values()),SETN1_ties=[x for x in c['placements'] if x['role']=='source_bound_SETN1_tie'],source_PG_terminal_projection_count=c['source_PG_rail_projection_terminal_count'],source_PG_projection_PASS=True,actual_source_ICG=icg,CLK_origin_LEF_GCLK_M1_bbox_DBU=[v+icg['bbox_DBU'][k%2] for k,v in enumerate(box)],clock_FF_replicas=8,reset_FF_replicas=4,clock_BUF=8*stages,reset_BUF=4*stages,balanced_new_branch_BUF_depth=stages,nets=nets,existing_WAKE8_recharged=False,added_sampling_edges=0,source_CLK_pin_sum_fF=max(c['clone_clock_pin_debit_SS_FF_fF'].values()),source_RESETN_pin_sum_fF=max(c['clone_reset_pin_debit_SS_FF_fF'].values()),same_net_clock_cut_not_eight_new_external_clocks=True,required_hold_wire_geometry=hold_wire_geometry(c['proposed_D_distribution'][0]),clock_skew_to_existing_siblings_ps_unqualified=True,root_driver_total_existing_plus_extra_load_unqualified=True,matching_existing_launch_capture_branch_required=True,reset_physical_ingress_unknown=True,proposed_reset_ingress_DBU=[278640,1788],proposed_reset_M4_guard_DBU=[274320,1728,278640,1848],reset_anchor_not_GCLK=True,extra_reset_cut_track_guard_reservation=3,existing_source_clock_cut_tracks=g['clock_cut_track_reservation'],tracks_not_routed_availability=True)
    # Increment only the local branch BUF bodies beyond b328's one clone CLK leaf.
    added=sum((1686 if k=='q' else 362)*(v['clock_BUF']+v['reset_BUF']-1) for k,v in result.items())
    delta=added*.10206*2/1e6
    reset_added=sum((1686 if k=='q' else 362)*v['full_existing_reset_positive_BUF'] for k,v in result.items())
    reset_delta=reset_added*.10206*2/1e6
    events=flow['events']
    for e in events:
        if any(e[k]!=v for k,v in i['identity'].items()):raise ValueError('wrong accepted event phase/owner')
    rawroots=[e for e in events if e['kind']=='root_row_accept']
    writes=[e for e in events if e['kind']=='VM_write_accept']
    visible=[e for e in events if e['kind']=='final_destination_visible']
    if len(rawroots)!=576 or {e['b'] for e in rawroots}!=set(range(576)):raise ValueError('lost row ownership')
    if any(e['edge']+1!=next(w['edge'] for w in writes if w['b']==398720+e['b']) for e in rawroots):raise ValueError('wrong registered writer deadline')
    if {e['a'] for e in visible}!={w['b'] for w in writes}:raise ValueError('lost destination visibility')
    aq=sorted(x['edge'] for x in events if x['kind']=='AQ_output_capture');activation=sorted(x['edge'] for x in events if x['kind']=='activation_field_accept')
    if len(aq)!=80 or len(activation)!=80:raise ValueError('missing actual beat')
    roots={s:i['per_shard_accepted_cadence'][f'{s}:root_row_accept']['edge_counts'] for s in ('0','1')}
    bw=i['boundary_widths'];root_rates={s:{t:n*bw['root_wire_bits_per_port'] for t,n in r.items()} for s,r in roots.items()}
    def fifo_report(port_count):
        queue=[];fin=[];maximum=0
        for t in range(414,1000):
            queue.extend(sorted([e for e in rawroots if e['edge']==t],key=lambda e:e['a']))
            maximum=max(maximum,len(queue))
            for _ in range(min(port_count,len(queue))):
                e=queue.pop(0);fin.append(dict(row=e['b'],root=e['a'],root_ready=e['edge'],source_shard=e['a']//64,VM_visible=t+1,extra_edges=t-e['edge']))
            if len(fin)==576:return dict(ports=port_count,writer_bits_per_edge=port_count*bw['writer_wire_bits_per_port'],last_VM_visible=fin[-1]['VM_visible'],maximum_queued_roots=maximum,maximum_additional_queue_edges=max(x['extra_edges'] for x in fin),all576_preserved=(len({e['row'] for e in fin})==576))
        raise ValueError('failed finite root drain')
    cfg_bound=(1000/1.2)-60-25
    return dict(schema='DS_SELECTED_CALLER_PHYSICAL_BRANCH_AND_I66_EDGES_V1',candidate=i['candidate'],input_origins=origins,generator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),source_caller_commit='b32857642896e6f15333682feafaf9c0b3011061',same_BST_source_model=bst,selected_enable_commit=origins['enable8d6.json.gz']['commit'],branch_construction=result,station_count=len(stations),station_cell_floor_delta_mm2_at50pct=delta,area=dict(prior_screen_mm2=j['screen_mm2'],committed_enable8d6_revision_delta_mm2=enable_revision_delta,enable_revision_delta_charged_once=True,positive_additional_branch_floor_mm2=delta,positive_full_existing_reset_floor_mm2=reset_delta,source_correct_BST_additional_floor_mm2=bst['total_additional_cell_floor_mm2'],full_existing_reset_new_BUF_cells=reset_added,original_reset_and_new_clone_nodes_not_doublecounted=True,screen_mm2=j['screen_mm2']+delta+enable_revision_delta+reset_delta+bst['total_additional_cell_floor_mm2'],remaining_mm2=858-j['screen_mm2']-delta-enable_revision_delta-reset_delta-bst['total_additional_cell_floor_mm2'],containment_credit=0,unchanged_frames={'q':[510.84,151.20],'BF':[1002.89,157.68]},PG_actual_row_pin_union_proven=False,fit=False),clock_contract=dict(wire_segment_max_um=max_wire/1000,pin_cap_fF=p['clock']['maximum_pin_cap_fF'],wire_cap_fF=p['clock']['wire_cap_fF'],buffer_output_plus_wire_slew_upper_ps=p['clock']['SS_cell_plus_2p2_wire_slew_ps'],skew_budget_ps=25,SS_setup_uncertainty_ps=60,FF_hold_uncertainty_ps=25,SS_min_high_low_pulse_ps=p['clock']['SS_macro_min_high_low_pulse_ps'],existing_plus_new_source_clocks_need_equal_launch_capture_latency=True,installed_CTS_not_required_for_prebuild=True,FFhold_or_recovery_removal_qualified=False),accepted_I66=dict(source_commit='5a373d0fd11fe9445660af9872fd410b94788e38',actual_phase=i['identity'],runtime=i['runtime'],cfg=dict(read_edges=[34,58],capture_edges=[35,59],GO_edge=60,local_ports_per_shard=2048,bits_per_local_edge_per_shard=98304,accepted_words_per_shard=51200,one_edge_CLKQ_plus_mux_wire_capture_setup_ceiling_ps=cfg_bound,source_generic_capture_edges=1,hard_macro_two_edge_multicycle_with_II1_requires_bank_overwrite_hold_proof=True,weight274_CLKQ_not_transferred_to_configuration72=True,hard_cfg72_CLKQ_source_bound=False,hard_cfg72_capture_and_II1_not_qualified=True,two_edge_capture_if_needed_earliest_GO=61,two_edge_capture_to_first_activation_envelope_edges=21,envelope_is_not_hidden_latency_proof=True,ROM_ECC_required=False),activation=dict(payload_with_valid_bits=549,actual_AQ_producer_edges=aq,actual_accepted_edges=activation,paired_source_lead_edges=[b-a for a,b in zip(aq,activation)],lead_includes_existing_BST17_and_native_stalls_not_free_wire_slack=True,source_BST17_unchanged=True,additional_physical_transport_edges_unqualified=True,zero_latency_not_assumed=True),roots=dict(native_root_to_VM_edges=1,original_common_writer_peak_ports=128,peak_root_bits_per_shard=max(max(v.values()) for v in root_rates.values()),per_shard_actual_root_bits_by_edge=root_rates,writer_peak_bits_all_ports=128*63,fullwidth_port_contract=fifo_report(128),single_shared_port_counterfactual=fifo_report(1),minimum_no_serialize_common_ports=128,VM_sink_physical_home=None,physical_root_transport_qualified=False,lower_bound_delta_rule='For an additional registered physical hop H, each delivered root and its nativeVM+1 are delayedH unless actual upstream overlap is proved; no new ACK or golden K reassociation'),physical_cfg_activation_root_added_edges=None,no_global_ROM_ECC_seats=True,no_new_ACK=True,source_handoff_scope='actual I66 only; no other1148calls/fulltoken or physicalclock credit'),remaining=['legal actual VIA12/23 pin escapes and macrofield VDD/VSS array occupancy at proposed stations; source body clear is insufficient','existing plus clone leaf_clk0 route-depth/driver-cap/skew union, not just eight same-depth paths','rst_n source ingress and reset recovery/removal with exact full clock/reset loading','hard4096x72 configurationROM measuredCLKQ/II and source-bound held loader capture','actualactivation crossing and complete128port root/writer commonVM home service/link lanes'],full_context_build_admitted=False,local_construction_is_model_only=True,new_jobs=0),stations

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False);m,s=build()
    (a.out/'model.json').write_text(json.dumps(m,indent=2,sort_keys=True)+'\n')
    (a.out/'stations.json').write_text(json.dumps(s,indent=2,sort_keys=True)+'\n')
