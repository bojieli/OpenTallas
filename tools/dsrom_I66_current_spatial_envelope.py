#!/usr/bin/env python3
"""Freeze one conservative DS interstage request and price current scalar/XN ABI.
No new source-state calendar: the committed owner calendar supplies all costs.
No invented package adjacency, PHY bandwidth, data STA or capture manufacturing.
"""
import argparse,gzip,hashlib,json,math,re
from pathlib import Path
import dsrom_I66_stage_provider as P
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'results/uarch/dsrom_I66_current_spatial_envelope_20261002'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def inputs():
    path=BASE/'inputs';receipts=json.loads((path/'origins.json').read_text());data={}
    for row in receipts:
        p=path/row['copy']
        if sha(p)!=row['sha256']:raise ValueError('Changed pinned spatial input '+row['copy'])
        if p.name!='cells.lef.gz':
            raw=gzip.decompress(p.read_bytes()) if p.suffix=='.gz' else p.read_bytes()
            data[row['copy'].removesuffix('.gz')]=json.loads(raw)
        source=ROOT/row['current_source']
        if not source.exists() or sha(source)!=row.get('source_sha256',row['sha256']):raise ValueError('Current source drift '+row['current_source'])
    return data,receipts

def lease_screen(f,r,timeout):
    # Existing calendar is authoritative. Body221+header236 remains2flits;
    # mathematical transport price does NOT prove the proposed field binding.
    v=P.reuse_price([288,289,290,291,292,293],f,r,ACK_TIMEOUT=timeout)
    w=P.reuse_price([288,289,290,291,292,293],f,r,ACK_TIMEOUT=timeout,W1_only=False)
    return dict(six_W1_current_twoflit=v,twelve_W1_W3_current_twoflit=w,
                six_W1_full2048_descriptor_percopy_edges=v['per_expert_serial_transport_edges']+126,
                six_W1_full2048_descriptor_reuse_edges=v['reuse_serial_transport_edges']+126,
                twentyone_edge_command_reduction_per_call_is_only_transport=True,
                capture_scalar_reads_per_edge=1,registered_lease_check_per_call_edges=1,
                actual_fullprogram_latency=None,no_loss_proven=False)

def capture_cost(d):
    bank=d['capture.json']['stages']['0']
    if bank!=d['capture.json']['stages']['1']:raise ValueError('Stage bank allocation differs')
    depths=bank['bank_depths']
    if len(depths)!=128 or sum(depths)!=576:raise ValueError('Bank row conservation')
    lef=gzip.decompress((BASE/'inputs/cells.lef.gz').read_bytes()).decode()
    def area(master):
        block=re.search(r'MACRO '+master+r'\b(.*?)END '+master,lef,re.S)
        if not block:raise ValueError('Missing LEF master '+master)
        w,h=map(float,re.search(r'SIZE\s+([.\d]+)\s+BY\s+([.\d]+)',block[1]).groups())
        return w*h
    masters={n:area(n+'_ASAP7_75t_R') for n in ['DFFHQNx1','DFFASRHQNx1','NAND2x1','INVx1','XOR2x1','BUFx4']}
    # Positive illustrative circuit: raw nonreset FF; resettable control;
    # QN restoration on every stored bit; NAND3+INV per 2:1 bit mux.
    raw=bank['exact_FF_record_bits'];ctrl=bank['candidate_control_bits']
    mux=bank['bank_local_write_select_2to1_bit_equivalents']+bank['scalar_read_mux_2to1_bit_equivalents']
    eq=bank['row_membership_compare_bits']
    components=dict(raw_FF=raw*masters['DFFHQNx1'],control_ASR_FF=ctrl*masters['DFFASRHQNx1'],
       QN_restore=(raw+ctrl)*masters['INVx1'],mux_NAND_INV=mux*(3*masters['NAND2x1']+masters['INVx1']),
       equality_XOR=eq*masters['XOR2x1'],equality_reduce_NAND=576*15*masters['NAND2x1'])
    reserve=2*sum(components.values())/1e6
    shards=[dict(shard=i,write_ports=64,seats=sum(depths[64*i:64*(i+1)]),
       raw69_bits=69*sum(depths[64*i:64*(i+1)]),fill_read_index_bits=384,
       row_seen_bits=sum(depths[64*i:64*(i+1)])) for i in range(2)]
    clock_levels=[];n=raw+ctrl
    while n>1:
        n=math.ceil(n/32);clock_levels.append(n)
    reset_levels=[];n=ctrl
    while n>1:
        n=math.ceil(n/32);reset_levels.append(n)
    tree_proxy=2*(sum(clock_levels)+sum(reset_levels))*masters['BUFx4']/1e6
    return dict(origin='ef6da37de6f6c641936615f61825628c2db7b8d4',owner_banks=128,seats=576,
       exact_FF_bits=raw+ctrl,bank_depths=depths,per_shard=shards,common_owner_context_bits=124,
       context_replicas_not_free=True,write_bits_per_edge=8832,write_context_fanout=128,
       row_decode_destinations=576,mux_2to1_bit_equivalents=mux,row_compare_bits=eq,
       selected_FF_record_carrier_bits=69,pow2_memory_alternative_seats=640,
       pow2_memory_alternative_extra_raw_bits=4416,physical_memory_provider_selected=False,
       LEF_master_areas_um2=masters,illustrative_cell_components_um2=components,
       illustrative_50pct_reservation_mm2=reserve+tree_proxy,logic_state_50pct_mm2=reserve,
       illustrative_clock_reset_32way_levels=[clock_levels,reset_levels],
       illustrative_clock_reset_BUF_reserve_mm2=tree_proxy,clock_reset_32way_not_electrically_admitted=True,
       proxy_not_mapped_area=True,
       body_containment_in_old_return_reserve_proven=False,return_credit_mm2=0,
       clock_reset_decode_buffer_route_PG_hold_additions_mm2=None,
       scalar_drain_first=423,scalar_drain_last=998,actual_remote_home_visibility=False,
       actual_program_deadline=None,physical_slot_fit=False)

def whole_join(d,cap,corridors):
    old=d['caller.json']['whole_reticle_join'];enable=d['enable.json']['cases']
    exact=[enable[k]['conservative_50pct_core_reservation_um2'] for k in ['q','bfcolumn']]
    previous=[x['core_um2_per_element'] for x in old['enable']]
    delta=sum((new-prior)*x['instances_per_shard']/1e6 for new,prior,x in zip(exact,previous,old['enable']))
    terminal=d['terminal.json']['cost']['reserve_delta_mm2_at50pct']
    base=old['screen_mm2']+delta+terminal
    # New capture control/circuit cannot be subtracted from inherited return
    # without the actual instance/rectangle union. This is a no-containment
    # counterfactual, not asserted necessary die area.
    total=base+corridors+cap['illustrative_50pct_reservation_mm2']
    return dict(predecessor_screen_mm2=old['screen_mm2'],exact_enable_core_um2=exact,
       replacement_enable_delta_mm2=delta,allowed_terminal_delta_mm2=terminal,
       corrected_predecessor_screen_mm2=base,new_two_port_corridor_reservation_mm2=corridors,
       capture_whole_owner_proxy_mm2=cap['illustrative_50pct_reservation_mm2'],
       no_containment_whole_owner_on_one_die_screen_mm2=total,
       no_containment_remaining_mm2=858-total,necessary_deficit_mm2=None,
       inherited_fixed_service_route_clockPG_mm2=418.269164,
       existing_return_capture_containment_credit_mm2=0,
       existing_clock_construction_replacement_credit_mm2=0,
       actual_new_clock73_union_vs_inherited_clock_tree_containment=None,
       field_sites_per_die=2048,q_sites_per_die=1686,BF_sites_per_die=362,
       q_frame_um=[510.84,151.2],BF_frame_um=[1002.89,157.68],
       all_compiled_macros_per_die=8192,
       field_frame_mm2=(1686*510.84*151.2+362*1002.89*157.68)/1e6,
       field_frame_is_contained_in_predecessor_not_new_addition=True,
       inherited_fixed_term_cannot_be_treated_as_free_rectangle=True,
       selector_1p68242_charged_once=True,
       selector_station_cycles_per_call=226,selector_service_cycles_per_call=142,
       selector_nine_calls_cycles=3312,WAKE_recharge=0,ROM_ECC_recharge=0,
       packing_overlap_free=False,positive_margin_is_not_fit=True,
       next_binding='Arch actual field/service/port/capture rectangle union with PG OBS pins and clock/reset roots; Nash scalar capture/VM lease endpoint')

def build():
    d,receipts=inputs();old=d['spatial_request.json'];s=old['spatial'];owners=d['owners.json']['phase_choices']
    if len(owners)!=384 or {o['expert'] for o in owners}!=set(range(384)):raise ValueError('Owner coverage')
    for o in owners:
        e=o['expert'];stage=0 if e<288 else 1;phase=10+3*e if stage==0 else 3*(e-288)
        if (o['stage'],o['phase'],o['source_key_word'])!=(stage,phase,2149580800+4096*e):raise ValueError('Exact owner mismatch')
    center=s['source_HUB_VM_center_DBU'];shore=s['proposed_east_shore_center_DBU']
    distance=sum(abs(x-y) for x,y in zip(center,shore))/1000
    if distance!=s['local_L1_route_um']:raise ValueError('Changed source reach')
    segments=math.ceil(distance/s['source_wire_segment_limit_um']);local_edges=2*segments
    flight=2*local_edges+2*s['CDC_edges_per_end']+s['PHY_flight_edges']
    if flight!=1337:raise ValueError('Envelope must be repriced, not retuned')
    widths=dict(data=256,flitCRC=32,packetCRC=32,seq=8,last=1,valid=1)
    forward=sum(widths.values());reverse=dict(ready=1,ACKvalid=1,ACKseq=8,ACKok=1,external_remote_credit=1)
    duplex=2*(forward+sum(reverse.values()));channel=2*duplex*s['source_horizontal_pitch_um']
    corridor=channel*distance/1e6;strip=.5*1.5
    timeout=old['timeout']['proposed_ACK_TIMEOUT']
    try:P.input_packets(0,flight,flight)
    except ValueError as e:default=dict(verdict='FAIL_DEFAULT1024',reason=str(e))
    else:raise ValueError('Default source timeout failure was lost')
    clock=d['clock_union.json']
    cap=capture_cost(d);whole=whole_join(d,cap,2*(strip+corridor))
    source=P.source_contract()
    # Candidate storage lower bounds; never subtract existing raw metadata
    # body or turn allocation/compiler bit counts into manufacturing credit.
    cdc_gross=duplex*s['CDC_depth_flits_reserved']
    port_bits=131259+duplex*local_edges+cdc_gross
    masters=cap['LEF_master_areas_um2']
    port_floor=2*port_bits*(masters['DFFHQNx1']+masters['INVx1'])/1e6
    return dict(schema='opentallas.dsrom.current-I66-spatial-provider-request.v1',candidate='DS4096-TP4-S58-PAR2-NP2048',
       provider_id='S58-NN-STAGE-LINK-PRELOAD-CAPTURE-v1',enabled_default=False,
       source_receipts=receipts,authoritative_calendar_tool='tools/dsrom_I66_stage_provider.py',calendar_tool_sha256=sha(ROOT/'tools/dsrom_I66_stage_provider.py'),
       ownership=dict(local_stage=0,local_EIDs=[0,287],remote_stage=1,remote_EIDs=[288,383],TP4_rank_preserved=True,PAR2_shards_per_owner=2,
                      logical_adjacent_links=57*4,logical_endpoint_wrappers=57*4*2,actual_physical_adjacency=None,actual_endpoint_instances=None,
                      actual_common_VM_hub_shard_home=None,ordered_six_plus_sharedlast_unchanged=True),
       boundary=dict(forward_fields=widths,forward_bits=forward,reverse_fields=reverse,reverse_bits=sum(reverse.values()),full_duplex_bits=duplex,
                     source_credit_advertisement_output_present=False,remote_credit_input_producer=None,clock_reset_reference_not_in684=True,
                     physical_PHY_lanes_rate_encoding_and_grant_II=None,source_parameters=source),
       spatial=dict(reticle_orientation_width_height_mm=[33,26],retained_HUB_VM_bbox_DBU=s['source_HUB_VM_bbox_DBU'],
                    retained_HUB_VM_center_DBU=center,actual_pin_coordinates=None,proposed_east_shore_DBU=shore,
                    requested_both_legs_L1_um=distance,source_clockBUF_segment_bound_um=s['source_wire_segment_limit_um'],
                    bound_not_data_characterization=True,segments_per_leg=segments,requested_register_edges_per_leg=local_edges,
                    requested_forward_edges=flight,requested_reverse_edges=flight,CDC_edges_per_end_requested=2,PHY_edges_requested=1,
                    proposed_east_west_strips_mm=s['proposed_neighbor_strips_mm'],directional_M4_pitch_um=s['source_horizontal_pitch_um'],
                    halfpool_reservation_width_um=channel,actual_available_tracks_PG_OBS_via_pin_union=None,
                    reference_package_flight_not_bounded=True,physical_successful_service_bound=None),
       state_and_area=dict(TXbits=65536+98,RXbits=65536+89,endpoint_wrapper_bits=131259,
                           per_port_wrapper_pipeline_CDC_bits=port_bits,
                           per_port_FF_QN_restore_50pct_proxy_mm2=port_floor,
                           per_port_remaining_strip_after_state_proxy_mm2=strip-port_floor,
                           endpoint_CRC_mux_clock_reset_PG_wire_cost_unbound=True,
                           port_state_proxy_contained_in_strip_not_added_again=True,
                           requested_local_port_pipeline_FFbits=duplex*local_edges,
                           previous_CDC1400bit_screen_incomplete_for_full684_width=True,
                           requested_four_entry_full_duplex_CDC_gross_bits=cdc_gross,CDC_pointer_control_bits_and_adequacy=None,
                           command_body_proposed_bits=221,command_source_fields_proved=False,header_ABI_bits=236,header_carrier_bits=256,
                           source_full2048_descriptor_preserved_as_alternative=True,
                           root_capture_rows=576,root_capture_ports=128,capture_data32bits=576*32,capture_occupancy_bits=576,capture_sticky_fault_bits=1,
                           capture_information_bits_lowerbound=19009,source_root_wire_bits_per_port=69,raw69wire_is_not_all_required_stored_state=True,
                           actual_capture_banking_padding_tag_multiplex_control_area=cap,raw69body_area_credit=0,
                           actual512b_read_write_holds_mux_and_control_cost=None,port_strip_mm2=strip,corridor_mm2=corridor,
                           per_port_reservation_mm2=strip+corridor,two_neighbor_ports_reservation_mm2=2*(strip+corridor),
                           gross_FF_floor_not_added_to_containing_port_reservation=True,inherited_service_containment_credit=0,
                           actual_root_capture_endpoint_and_field_placement_union=None),
       composed_whole_area=whole,
       native_ports=dict(cfg_local_ports_per_shard=2048,cfg_word_bits=48,
          cfg_local_bits_per_native_edge=98304,local_cfg_ports_not_link_bandwidth=True,
          source_cfg_last_capture_edge=59,source_GO_edge=60,source_cfg_delivery_margin_edges=1,
          active_FP4_broadcast_bits=549,PHW10_full_broadcast_bits=1632,BST=17,
          root_ports_per_shard=64,root_wire_bits_per_port=69,writer_bits_per_port=63,
          paired_main_capture_bits=548,main_capture_to_lane_edges=1,
          actual_parent_IO_setup_hold_and_route_ps=None),
       clock_context=dict(current_union_source_commit='283ed0249',named_buffer_count=73,named_endpoint_count=1100,
                          native_hold_wire_um=[18.972,5.697],
                          matched_leaf_native_skew_ceiling_ps=25,source_sink_slew_ceiling_ps=320,
                          twoedge_macro_capture_remaining_after_SS_clkq_and60ps_uncertainty_ps=767.5732666666666,
                          remaining_after25ps_skew_ps=742.5732666666666,
                          actual_capture_setup_mux_wire_budget_closed=False,
                          reset_release_recovery_removal_route_closed=False,
                          new_WAKE_or_clone_or_hold_recharge=0,via_root_reset_open=True,
                          native_via_FF_cap_budget_fF=clock['cases']['q']['FF_native_via_cap_budget_fF'],
                          native_via_SS_R_budget_kohm=clock['cases']['q']['SS_extra_via_resistance_budget_at_full_cap_kohm'],
                          source_nominal_stream_ps=2500/3,SS_FF_qualified=False),
       timeout=dict(source_default=1024,default=default,requested_optin=timeout,actual_selected=None,retries_not_latency_hiding=True),
       current_scalar_reuse_prices=dict(positive1each_direction=lease_screen(1,1,1024),requested1337each_direction=lease_screen(flight,flight,timeout)),
       prerequisites=['exact221bit source body/descriptor arithmetic identity proof','actual684boundary credit/PHY/CDC grant semantics and pins',
                      'native data/ACK/credit routing and registered stage timing','source producer visibility and all384 accepted owner/consumer deadlines',
                      'reviewed576-seat banks cell/PG/clock/reset/pin placement and no-ready128writer delivery fit','exclusive CDMA/XB extents and result scalar packing',
                      'named clock73/1100 root/reset/via source constraints'],
       physical_build_admitted=False,selected_PHY=False,fit_proven=False,physical_endpoint_qualified=False,
       full_singleuser_MTP_iteration_latency=None,fulltoken_rate_qualified=False,new_jobs=[])
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(build(),indent=2,sort_keys=True)+'\n')
