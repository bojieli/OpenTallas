"""Selected minimum W11 protected-publication construction and finite service.
Measured native leaves size the default-off candidate; route validates it later.
"""
from pathlib import Path
import argparse,hashlib,json,math
ROOT=Path(__file__).resolve().parents[1]
NS='results/uarch/dsrom_s81_minimum_protected_group_20261004'
ID='DSROM-S81-W11-NB2-RC6-K4-WQD4-RDREG1-HELD2-CAP1'
T=1000/.9

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def tree(n):
    total=0
    while n>1:n=math.ceil(n/8);total+=n
    return total

def bank_calendar(start=0):
    stages=[('exclusive_old_read_and_RDREG',2),('old_decode',2),('old_owner83_check',1),('mask_merge',1),('encode',1),('matched_all_six_data_and_check_write',1),('exclusive_postverify_and_RDREG',2),('postverify_decode',2),('postverify_owner83_check',1),('held_receipt',1)]
    edge=start;out=[]
    for name,count in stages:out.append({'stage':name,'begin_edge':edge,'end_edge':edge+count,'domain':'serial_0.9_target','occupied_edges':count});edge+=count
    return out

def service(rows_ahead=0,route_stations=16):
    if type(rows_ahead) is not int or not 0<=rows_ahead<=3:raise ValueError('WQD4 includes the active row; at most three ahead')
    if route_stations!=16:raise ValueError('One selected 11-mux + five relay candidate, no stage sweep')
    local=bank_calendar()[-1]['end_edge']
    # Co-derived 4:3 clocks/reset: three receiver edges includes capture/phase.
    # Field: CDC3 + held decode2 + owner compare1 + counted update1 + encode2.
    fast=3+2+1+1+2
    # Bank: reverse CDC3 + held decode2 + owner compare1 + registered release1.
    slow=3+2+1+1
    occupied_ns=local/.9+fast/1.2+slow/.9
    ii=math.ceil(occupied_ns*.9)
    # Two packet routes are explicit independent lanes, not two services on one lane.
    route_ns=route_stations/.9
    # Four fast input edges/superframe plus positive three-slow admission capture.
    admission_ns=4/1.2+3/.9
    return {'local_RMW_edges':local,'local_RMW_ns':local/.9,'counted_return_fast_edges':fast,
            'reverse_release_slow_edges':slow,'occupied_bank_ns_bound':occupied_ns,
            'bank_service_II_slow_edges':ii,'bank_service_II_ns':ii/.9,
            'active_RMW_capacity_per_bank':1,'bank_pipeline_capacity_rows':1,
            'WQD_total_owned_rows_including_active':4,'rows_ahead_bound':rows_ahead,
            'predecessor_wait_ns':rows_ahead*ii/.9,'two_route_lanes':2,
            'route_stations':route_stations,'route_latency_ns_bound':route_ns,
            'route_service_II_slow_edges_target':1,'admission_gear_ns_bound':admission_ns,
            'accepted_head_to_captured_retirement_ns_bound':admission_ns+route_ns+rows_ahead*ii/.9+occupied_ns,
            'maximum_payload_write_bytes_per_slow_edge_average':2*32/ii,
            'successful_service_assumptions':['co-derived 4:3 clocks and matched reset enrollment','fixed positive route latency within reserved station count','all old-read/write/postverify ports exclusively granted before GO','no bad checked word; fault retains whole accepted phase and forbids next GO','actual receiver accepted counted update and return before credit release'],
            'not_measured_group_II':True,'source_clock_qualified':False}

def build(root=ROOT):
    root=Path(root);ns=root/NS
    manifest=json.loads((ns/'manifest.json').read_text())
    for name,expected in manifest.items():
        if sha(ns/name)!=expected:raise ValueError('Pinned input/evidence changed: '+name)
    read=lambda p:json.loads((ns/p).read_text())
    measured=read('evidence/selected_held_landing/record.json')
    original=read('evidence/original_registered_FAIL/record.json')
    ctrl=read('inputs/publication_control.json');facts=read('inputs/cell_prices.json')['facts']
    macros={x:read('inputs/'+x+'_macro.json') for x in ('data','check')}
    cuts={}
    for name,v in measured['results'].items():
        if any(v['timing'][c]['electrical_violations'] for c in ('ss','ff')):raise ValueError('Held cycles cannot waive electrical limits')
        need=T-v['timing']['ss']['setup_slack_ps']
        slow=math.ceil((need+25)/T);fast=math.ceil((need+25)/(1000/1.2))
        hold=v['timing']['ff']['hold_slack_ps']-25
        if hold<0:raise ValueError('Capture branch cannot absorb selected adverse skew')
        cuts[name]={'serial_held_edges':slow,'streaming_held_edges':fast,
                    'SS_required_period_ps_including60unc':need,
                    'serial_remaining_wire_ps_after25skew':slow*T-need-25,
                    'streaming_remaining_wire_ps_after25skew':fast*(1000/1.2)-need-25,
                    'FF_hold_ps_after25unc_and25adverse_skew':hold,
                    'fanout_and_capture_BUF_count':v['construction']['buffer_count'],
                    'held_input_and_owner_required':True,'not_a_one_per_edge_pipeline':True}
    if {n:c['serial_held_edges'] for n,c in cuts.items()}!={'encode':1,'decode':2,'equal83':1,'merge256':1}:raise ValueError('Selected cut timing changed')
    # Dedicated codec/guard stages: these are distinct from controller state-update muxes.
    replicas={'encode':68+4,'decode':68+4,'equal83':6+2+6,'merge256':2}
    price={n:v['SS']['area_um2'] for n,v in facts.items()}
    counts={n:0 for n in price}
    for n,r in replicas.items():
        for cell,num in measured['results'][n]['cell_counts'].items():counts[cell]+=num*r
    # Each codec physical input/output register is positively charged, not an alias
    # of the controller's 4896 coded state FF. Held owner tags cover ten local cuts.
    tag_FF=2*10*144;CDC_FF=2*2*3*144
    arb_FF=6*216+2*144 # six held protected read requests and two bank grants
    valid_ASR_FF=32*72 # protected pipeline-valid tokens; data FF not reset
    counts['DFFHQNx1_ASAP7_75t_R']+=tag_FF+CDC_FF+arb_FF
    counts['DFFASRHQNx1_ASAP7_75t_R']+=valid_ASR_FF
    counts['INVx1_ASAP7_75t_R']+=tag_FF+CDC_FF+arb_FF+valid_ASR_FF
    controllerFF=ctrl['state_total_coded_FF']
    allFF=counts['DFFHQNx1_ASAP7_75t_R']+controllerFF+valid_ASR_FF
    clkbuf=tree(allFF)+tree(24) # separate clock groups; macro leaves <=4 to price load
    macro_clkbuf=6+1
    clkbuf=tree(allFF)+macro_clkbuf
    resetbuf=tree(valid_ASR_FF)
    ties=valid_ASR_FF # one actual SETN tie per added ASR valid-token FF
    branchbody=(clkbuf+resetbuf)*price['BUFx4_ASAP7_75t_R']+ties*0.04374
    nativebody=sum(counts[n]*price[n] for n in counts)
    # Replace the explicitly itemised bare controller W6 floor, never sum it again.
    controller_no_bare_codec=ctrl['cost']['minimum_control_only_cell_mm2_floor']-ctrl['cost']['actual_W6_codec_no_CSE_body_mm2']
    logicbody=controller_no_bare_codec*1e6+nativebody+branchbody
    w=6*(172.8+2*12.96); macro_h=2*(41.04+2*12.96)+2*(17.82+2*12.96)
    annex=math.ceil((2*logicbody/w)/.27)*.27
    # Two separate positive 25.92um signal/PG/clock corridors, not free tracks.
    outline_h=macro_h+annex+2*25.92
    placement=[]
    for kind,base,h in [('data',0,41.04),('check',2*(41.04+25.92),17.82)]:
        for bank in range(2):
            for copy in range(6):
                j=macros[kind]['area'];x=12.96+copy*(172.8+25.92);y=base+12.96+bank*(h+25.92)
                placement.append({'instance':f'{kind}_b{bank}_c{copy}','bank':bank,'copy':copy,'orientation':'R0','macro_bbox_um':[x,y,x+j['macro_width_um'],y+j['macro_height_um']],'halo_um':12.96})
    macrobody=sum(12*macros[k]['area']['macro_area_um2'] for k in macros)
    numeric=service()
    return {'schema':'opentallas.uarch.DSROM.S81.minimum_protected_W11.v1','candidate':ID,
        'selected_provider':{'module':'ot_v41_vm_group_phys','source_sha256':sha(ns/'inputs/group.sv'),'NB':2,'RC':6,'K':4,'WQD':4,'RDREG':1,'physical_replicas_target':128,'replica_home_fit':None,'bank_codec_publication_clock_GHz_target':.9,'field_clock_GHz_target':1.2,'clocks_qualified':False,'native_bank4_provider_credit':False},
        'mutable_codec':{'source':'ot_gpu_w6_secded_pkg.sv','source_sha256':sha(ns/'inputs/w6_codec.sv'),'payload64_protected72':True,'owner83_held_coded144':True,'cuts':cuts,'source_corrected_polarity':'DFFHQ QN restores INV; actual EN feedback 3NAND+INV+2BUF; fixed fanout8; one final BUF per internal capture D landing','register_and_logic_buffer_contraction_verified':True,'held_feedback_is_positively_mapped_and_measured':True,'capture_enable_source_arrival_and_clock_enable_loaded_control_unqualified':True,'no_commercial_reliability_claim':True},
        'ports':{'old_read':'copy0 data+check per bank only with exclusive grant','postverify':'all6 data+check copies each bank same immutable row','check_master':'ot_sram_1rw_256x64_m4_r2c2','check_1RW_mutually_exclusive_windows':['old_read','write','postverify'],'instances':{'data':12,'check':12},'check_useful_bits_per_row_per_copy':32,'check_unused_charged_bits_per_row_per_copy':32,'phase_preGO':'reserve whole accepted phase, both route lanes, bank slots, actual read/write exclusions before NOREADY field GO','CKV_DMA_read_priority':'request is not accept; six coded216 held request seats plus two coded144 bank grants; preGO grant waits every accepted old read/write; new DMA command admission is excluded upstream because native DMA has no ready; native CKV priority retained after publication; never force ready','first_consumer':{'PC':'L0.I9','src':419776,'dst':51648,'n':320,'read_reenabled_only_after':'allcopy checked publication AND matched counted captured return; request held until actual native read grant'},'all6copy_visibility':True,'write_ACK_is_not_request_acceptance':True},
        'macro_corners':{k:{c:macros[k]['timing'][c] for c in ('ss','ff')} for k in macros},
        'calendar':bank_calendar(),'read_service':{'request_CAPTURE_IS_ACCEPT_only_when_actual_grant':True,'held_request_capacity_per_native_read_class':1,'protected_request_bits_per_class':216,'owner83_compare_edges':1,'request_capture_edges':1,'macro_and_RDREG_edges':2,'checked_decode_edges':2,'checked_owner_edges':1,'registered_16way_bank_column_select_edges':4,'response_edges':1,'total_slow_edges_candidate':12,'II_slow_edges_capacity1':12,'latency_ns_candidate':12/.9,'read_context_timing_qualified':False,'mux_cut_basis':'four binary 2:1 levels, one held registered level per edge using measured buffered merge leaf as intrinsic size bound; actual loaded select placement still validates','pending_write_forwarding':'read grant only after all accepted writes published and queue drained; no unpriced forwarded unchecked data','arbitration_exclusion_required_before_GO':True},'service':numeric,'WQD4_max_service':service(3),
        'route':{'packet_source_bits':136,'coded_packet_register_bits':216,'lanes':2,'source_registered_mux_cuts':11,'additional_reserved_wire_stations':5,'target_total_cuts':16,'fwd_credit_and_reverse_positive_CDC_bound':True,'actual_wire_length_and_parent_pin_assignment':None,'qualified_route_latency':False},
        'area':{'data_macros_body_mm2':12*macros['data']['area']['macro_area_um2']/1e6,'check_macros_body_mm2':12*macros['check']['area']['macro_area_um2']/1e6,'controller_without_replaced_bare_codec_body_mm2':controller_no_bare_codec,'dedicated_native_cut_counts':counts,'dedicated_native_cut_body_mm2':nativebody/1e6,'controller_coded_FF':controllerFF,'tag_coded_FF':tag_FF,'CDC_coded_FF':CDC_FF,'held_arbitration_coded_FF':arb_FF,'pipeline_valid_ASR_coded_FF':valid_ASR_FF,'clock_BUF_count':clkbuf,'reset_BUF_count':resetbuf,'conservative_tie_count':ties,'clock_reset_tie_body_mm2':branchbody/1e6,'logic50_reservation_mm2':2*logicbody/1e6,'macro_plus_logic50_mm2':(macrobody+2*logicbody)/1e6,'joint_r4_not_summed':True,'replaced_exact_controller_bare_codec_floor_mm2':ctrl['cost']['actual_W6_codec_no_CSE_body_mm2'],'route_and_wholephase_suffix_separate_existing_debits':True,'full_group_logic_mapping_not_measured':True},
        'slot':{'scope':'one minimum group new candidate local vehicle, not selected parent fit','outline_um':[w,outline_h],'macro_zone_height_um':macro_h,'logic_annex_height_um':annex,'macro_instances':placement,'signal_PG_clock_corridors_um':25.92,'nominal48nm_tracks_per_corridor_layer':540,'actual_unblocked_tracks':None,'clock_style':'ClockC per-region shielded M8/M9 trunk; no mesh','clock_leaf_max_fanout':8,'macro_clock_leaf_max_fanout':4,'adverse_skew_target_ps':25,'FF_total_sinks':allFF,'macro_CLK_SS_load_fF':sum(12*macros[k]['timing']['ss']['clk_cap_ff'] for k in macros),'macro_CLK_FF_load_fF':sum(12*macros[k]['timing']['ff']['clk_cap_ff'] for k in macros),'native_macro_pin_track_gate_required':True,'PG_and_OBS_actual_exclusions':None,'parent_reticle_fit':None},
        'unified_S81':{'global_floor_r4_remains_historical_separate_branch':True,'whole_die_area_mm2':None,'token_delta_us':None,'single_user_latency_rule':'insert accepted publication dependency with measured component costs in max-plus graph; serialize actual bank occupation; do not sum every writer as exposed tail','conditional_one_nonoverlapped_empty_head_service_ns':numeric['accepted_head_to_captured_retirement_ns_bound'],'headline_token_rate':None},
        'admission':{'minimum_component_model_selected':True,'minimum_codec_and_slot_model_complete':True,'controller_RTL_agreement_required':['actual preGO read/write exclusion grant covers CKV and DMA','qualified write and postverify callbacks all6copies','held2 clock-enable and immutable owner through correction/fault','co-derived reset and positive CDC/returned credit, before next GO'],'engine_RTL_admitted':False,'group_PnR_admitted':False,'context_SS_FF_pass':False,'remaining_context_gate':'bind exclusive-grant and allcopy receipt source hooks to b41 controller; map one full group then verify native pin/OBS/PG/clock/route on this one slot'},'input_manifest_sha256':sha(ns/'manifest.json')}

def verify(root=ROOT):
    root=Path(root);ns=root/NS;got=build(root);want=json.loads((ns/'model.json').read_text())
    if got!=want:raise ValueError('Model replay differs')
    return got
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path);p.add_argument('--verify',action='store_true');a=p.parse_args();m=verify() if a.verify else build();s=json.dumps(m,indent=2,sort_keys=True)+'\n'
    if a.out:a.out.write_text(s)
    else:print(s)
