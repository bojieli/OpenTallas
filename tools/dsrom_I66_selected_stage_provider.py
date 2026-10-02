"""One source-owned S58 nearest-neighbour provider candidate; no RTL/physical admission.
The successful finite calendar is conditional on explicit service reservations.
Source TX/RX store-forward and ACK ownership are retained. No ECC storage.
"""
import argparse, gzip, hashlib, json, math
from pathlib import Path
import dsrom_selected_caller_branch_edges as B
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'results/uarch/dsrom_I66_selected_stage_provider_20261002'


def inputs():
    origin=json.loads((BASE/'inputs/origins.json').read_text());d={}
    for name,pin in origin.items():
        raw=(BASE/'inputs'/name).read_bytes()
        if hashlib.sha256(raw).hexdigest()!=pin['sha256']:raise ValueError('source pin '+name)
        plain=gzip.decompress(raw) if name.endswith('.gz') else raw
        d[name]=json.loads(plain) if '.json' in name else plain.decode()
    for s in ['state <= ST_COLLECT;', 'state <= ST_SEND;', 'state <= ST_WAIT_ACK;', 'ack_seq == packet_seq', 'if (ack_ok)', 'packet_mem [0:MAX_FLITS-1]']:
        if s not in d['tx.sv']:raise ValueError('TX ownership semantics changed')
    for s in ['state <= ST_DELIVER;', 'if (out_fire && out_last)', "expected_seq <= packet_seq + 1'b1", 'packet_mem [0:MAX_FLITS-1]']:
        if s not in d['rx.sv']:raise ValueError('RX delivery/ACK semantics changed')
    return d,origin


def packet(start,n,forward,reverse,link_II=1,delivery_II=1,timeout=None):
    """NBA edge recurrence for a first-attempt successful packet, n<=256.
    forward/reverse include all local-route/PHY/CDC latency, not free wires.
    n input accepts are continuous; reservations force every subsequent grant.
    ACK is generated only on RX last accepted delivery and observed later by TX.
    """
    if not 1<=n<=256 or min(forward,reverse,link_II,delivery_II)<1:raise ValueError('positive finite service required')
    last_collect=start+n-1
    first_send=last_collect+1;last_send=first_send+(n-1)*link_II
    first_receive=first_send+forward;last_receive=last_send+forward
    first_deliver=last_receive+1;last_deliver=first_deliver+(n-1)*delivery_II
    ack_seen=last_deliver+1+reverse
    if timeout is not None and ack_seen-last_send>timeout:raise ValueError('ACK timeout precedes bounded successful delivery')
    return dict(first_collect=start,last_collect=last_collect,first_send=first_send,last_send=last_send,
                first_receive=first_receive,last_receive=last_receive,first_deliver=first_deliver,last_deliver=last_deliver,
                matching_positive_ACK_seen=ack_seen,next_packet_credit=ack_seen+1,
                TX_WAIT_ACK_edges=ack_seen-last_send,flits=n,link_II=link_II,delivery_II=delivery_II)


def chunks(payload_bits,header_bits=128):
    # One whole header flit. 255 payload flits is largest source legal packet.
    if payload_bits<1 or not 0<header_bits<=256:raise ValueError('packet dimensions')
    payload_flits=math.ceil(payload_bits/256);res=[]
    while payload_flits:
        n=min(255,payload_flits);res.append(1+n);payload_flits-=n
    return res


class CaptureLease:
    """No-ready producer must own all worst-burst capture seats before GO.
    Successful link ACK alone never retires destination visibility ownership.
    """
    def __init__(self,capacity,identity):
        if capacity<576:raise ValueError('reserve all576 rows before nonbackpressured GO')
        self.identity=identity;self.rows={};self.visible=set();self.owner_idle=False
    def capture(self,row,identity,edge):
        if identity!=self.identity or row in self.rows or not 0<=row<576:raise ValueError('wrong/duplicate root owner')
        self.rows[row]=edge
    def destination(self,row,identity,edge):
        if identity!=self.identity or row not in self.rows or edge<=self.rows[row] or row in self.visible:raise ValueError('unowned/early destination visibility')
        self.visible.add(row)
    def retire(self,identity,positive_ACK):
        if identity!=self.identity or not positive_ACK or not self.owner_idle or len(self.visible)!=576:raise ValueError('source/visibility/ACK debt remains')
        return True


def build():
    d,pins=inputs();physical,_=B.build();i=physical['accepted_I66'];dispatch=d['dispatch.json'];clock=d['clock_contract.json']
    # Correct the previous construction's cfg unknown with Nash's actual72-bit macro receipt.
    cfg=clock['configuration'];cfg_remaining=833.3333333333334-60-cfg['SS_macro_clkq_ps']
    vm=next(x for x in d['services.json.gz'] if x['name']=='HUB_VM')['bbox_DBU']
    vm_center=[(vm[0]+vm[2])/2,(vm[1]+vm[3])/2]
    # Current source map 33x26 mm. Proposed east edge strip, same template for a peer.
    shore=[32750000,vm_center[1]]
    distance=B.L1(vm_center,shore)/1000
    max_segment=physical['clock_contract']['wire_segment_max_um']
    # Two registered edges per <= source-priced clock/BUF wire segment is a
    # requested prebuild service envelope, NOT a characterized data pipeline.
    segments=math.ceil(distance/max_segment);local_edges=2*segments
    flight=2*local_edges+4+1 # two local legs, two2-edge CDCs, one PHY-flight edge
    required_timeout=2*flight+256+1
    timeout=1<<(required_timeout-1).bit_length()
    # Actual emitted ME/QE fields plus route identity fit a single command flit.
    cmd_fields=dict(go=1,phase=10,positions_minus1=3,xbase=19,x_position_stride=19,obase=19,output_position_stride=19,row_format=2,owner_stage=6,key=32,EID=9,rank=2,generation=32,user=16,operation_sequence=32)
    command_bits=sum(cmd_fields.values())
    header=dict(generation=32,user=16,operation_sequence=32,owner_stage=6,rank=2,packet_kind=3,packet_ordinal=3,payload_bits=18,reserved=16)
    assert sum(header.values())==128
    # Complete input frame preload. No activation crossing or early AQ dispatch.
    timeline=[];next_edge=10
    for number,n in enumerate(chunks(5120*32)):
        t=packet(next_edge,n,flight,flight,timeout=timeout);t.update(kind='FP32_input_preload',ordinal=number);timeline.append(t);next_edge=t['next_packet_credit']
    input_visible=timeline[-1]['last_deliver']+1 # assembled last8words -> native registeredVM fence
    command=packet(max(next_edge,input_visible+1),1,flight,flight,timeout=timeout);command['kind']='owner_command';timeline.append(command)
    native_origin=command['last_deliver']+1
    # Actual accepted EID0 template only, NOT measured expert383 / whole program.
    source_last_root=native_origin+(419-10);source_idle=native_origin+(422-10)
    result=packet(source_last_root+1,chunks(576*63)[0],flight,flight,timeout=timeout);result['kind']='result_rows';timeline.append(result)
    final_visible=result['last_deliver']+1
    completion=packet(max(result['next_packet_credit'],source_idle+1),1,flight,flight,timeout=timeout);completion['kind']='owner_completion';timeline.append(completion)
    done=max(final_visible,completion['last_deliver']+1,completion['matching_positive_ACK_seen'],result['matching_positive_ACK_seen'],command['matching_positive_ACK_seen'])
    intrinsic=[];e=10
    for n in chunks(5120*32):
        t=packet(e,n,1,1,timeout=1024);intrinsic.append(t);e=t['next_packet_credit']
    c=packet(e,1,1,1,timeout=1024);orig=c['last_deliver']+1
    r=packet(orig+410,chunks(576*63)[0],1,1,timeout=1024)
    z=packet(max(r['next_packet_credit'],orig+413),1,1,1,timeout=1024)
    intrinsic_done=max(r['last_deliver']+1,z['matching_positive_ACK_seen'])
    # Exact source TX98/RX89 controls exclude combinational CRC temporaries.
    TX_bits=65536+98;RX_bits=65536+89
    endpoint_bits=TX_bits+RX_bits
    result_capture_bits=576*69+128
    assembler_bits=2048+64+128
    duplex_tracks=2*(330+12) #330 forward incl valid, 12 reverse ACK/ready/credit
    grid,_=B.read_inputs();M4=next(x for x in grid['grid.json']['layers'] if x['name']=='M4')
    assert M4['direction']=='HORIZONTAL'
    horizontal_pitch_um=M4['pitch']/1000
    route_width_um=duplex_tracks*horizontal_pitch_um*2 #50% directional track reservation, not extracted availability
    corridor_mm2=route_width_um*distance/1e6
    port_strip_mm2=.5*1.5
    pipeline_bits=duplex_tracks*local_edges
    CDC_bits=4*(330+12)+32 #four flits per direction plus positive pointer/sync floor
    FF_floor_bits=endpoint_bits+result_capture_bits+assembler_bits+pipeline_bits+CDC_bits
    FF_floor_mm2=FF_floor_bits*.2916*2/1e6
    # Block+corridor reservation contains only an FF floor screen, not placed logic.
    per_port_reservation=max(port_strip_mm2+corridor_mm2,FF_floor_mm2)
    stages=58;TP=4;boundaries=57*TP;endpoint_count=2*boundaries
    side_addition=2*per_port_reservation # busiest owner: two neighbour ports, on designated hub shard
    whole=physical['area']['screen_mm2']+side_addition
    native_cadence,_=B.read_inputs();native=native_cadence['I66.json']['per_shard_accepted_cadence']
    ce_by_edge={}
    for shard in ('0','1'):
        for edge,count in native[shard+':main_CE_accept']['edge_counts'].items():ce_by_edge[edge]=ce_by_edge.get(edge,0)+count
    max_packet_interval=packet(0,256,flight,flight,timeout=timeout)['next_packet_credit']
    return dict(schema='opentallas.dsrom.I66.selected-stage-provider.v1',generator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),physical_construction_source_commit='e0f3a30cc',physical_construction_model_sha256=hashlib.sha256((B.BASE/'r1/model.json').read_bytes()).hexdigest(),candidate='DS4096-TP4-S58-PAR2-NP2048',
      provider_id='S58-NN-STAGE-LINK-PRELOAD-CAPTURE-v1',selected_for_model=True,selected_for_RTL=False,source_pins=pins,
      topology=dict(stages=58,TP=4,shards_per_owner=2,neighbors='source-ordered stage i to i+1, same rank; TP reduction tree unchanged',I66_owner_counts=dispatch['stages'],I66_reachable_stage_distance_max=1,endpoints_all_neighbor_boundaries=endpoint_count,logical_links=boundaries,per_owner_ports_max=2,per_neighbor_packet_credit=1,physical_stage_package_coordinates_present=False,proposed_stage0_to1_neighbor_not_verified_package_adjacency=True),
      configuration=dict(actual_macro_SS_clkq_ps=cfg['SS_macro_clkq_ps'],actual_macro_FF_clkq_ps=cfg['FF_macro_clkq_ps'],single_edge_remaining_before_setup_wire_skew_ps=cfg_remaining,source_read_edges=[34,58],source_capture_edges=[35,59],source_GO_edge=60,actual_setup_mux_wire_clock_ps=None,source_local_ports_per_shard=2048,cfg48_bits_per_edge_per_shard=98304,cfg_is_local_not_interstage_bulk_traffic=True,source72_macro_context_qualified=False,previous_e0_unknown_bound_resolved_by_pinned_Nash_macro_receipt=True),
      compute_and_communication=dict(provider_MACs_per_cycle=0,unchanged_I66_symbolic_MACs=5120*576,source_paired_CE_total=sum(ce_by_edge.values()),source_paired_CE_peak_per_edge=max(ce_by_edge.values()),native_VM_input_bytes_per_edge=256,link_flit_bytes_per_granted_edge=32,maximum_packet_credit_interval_edges=max_packet_interval,useful_bytes_per_max_packet=255*32,conditional_credit_limited_useful_bytes_per_edge=(255*32)/max_packet_interval,matrix_MACs_per_input_byte=(5120*576)/(5120*4),MAC_per_weight_byte_not_changed=True,no_MAC_or_rate_qualification_transfer=True),
      parallel_capacity_requirements=dict(current_native_VM_bytes_per_edge=256,one_VM_beat_packet_flits=math.ceil((2048+128)/256),minimum_data_link_lanes_for_one_VM_beat_per_edge=9,one_VM_beat_credit_interval_even_with_minimal_positive_wire_edges=packet(0,9,1,1)['next_packet_credit'],one_VM_beat_credit_interval_under_spatial_envelope_edges=packet(0,9,flight,flight,timeout=timeout)['next_packet_credit'],required_one_packet_endpoint_contexts_if_no_prefetch_and_one_VM_beat_per_edge=packet(0,9,1,1)['next_packet_credit'],root_writer_payload_minimum_link_flits_per_edge=math.ceil(128*63/256),all_contexts_require_positive_RX_space_CRC_and_same_domain_owner_grants=True,these_are_necessary_bounds_for_stated_packet_policy_not_a_selected_parallel_successor=True,prefetch_available_window_from_actual_issue_graph=None,no_free_packet_context_or_shared_lane_overlap=True),
      ports=dict(command_fields=cmd_fields,command_bits=command_bits,command_lifecycle_fields_are_priced_proposal_not_existing_RTL=True,packet_header_fields=header,packet_header_bits=128,flit_data_bits=256,forward_total_bits=330,reverse_ACK_bits=10,reverse_ACK_ready_credit_bits=12,packet_max_flits=256,packet_credit=1,link_flit_II=1,RX_out_flit_II=1,preload_payload_bits=5120*32,preload_native_VM_vector_bits=2048,preload_VM_write_II=8,result_packet_payload_bits=576*63,no_ready_root_ports=128,no_ready_root_wire_bits=69,root_capture_rows_reserved_before_GO=576,no_ready_capture_peak_rows_per_edge=128,root_capture_slot_bits=69,result_decode_rows_per_edge_min=4,result_consumer_requires_exact_row_address_identity=True,selected_encoding='registered root69; unchanged row/address mapped writer63; full transaction header128 once per packet',ROM_ECC=False,link_CRC_retained=True),
      ownership=dict(input_frame_lease_words=5120,input_frame_lease='existing finite VM addresses46464..51583; never zero-cost extra storage; actual masked/native writer and ownership join required',input_VM_body_added_bits=0,input_VM_capacity_already_charged_not_removed=True,input_native64word_writes=80,input_assembler_bits=assembler_bits,input_preload_completion_before_owner_dispatch=True,post_lookup_owner_command_not_raw_ISA_passthrough=True,native_accepted_indexed_EID_and_stage_dispatch_adapter_still_required=True,root_capture_bits=result_capture_bits,root_capture_new_reserved_not_existing_return_free_credit=True,source_immutable_order=True,delivery_ACK_is_not_destination_visibility=True,release='all576 exact row/address visible + owner source idle + all matching accepted packetACKs',operation_sequence_bits=32,generation_bits=32,wire_packet_sequence_bits=8,sequence_reuse='only after sole packet debt drains; operation generation/sequence header prevents logical alias; reset/wrap handshake still source-gated'),
      spatial=dict(source_HUB_VM_bbox_DBU=vm,source_HUB_VM_center_DBU=vm_center,retained_HUB_VM_center_not_actual_pin=True,proposed_neighbor_strips_mm={'west':[0,vm_center[1]/1e6-.75,.5,vm_center[1]/1e6+.75],'east':[32.5,vm_center[1]/1e6-.75,33,vm_center[1]/1e6+.75]},source_west_local_L1_route_um=(vm_center[0]-250000)/1000,both_legs_long_east_bound_is_conservative_not_extra_stages_selected=True,proposed_east_shore_center_DBU=shore,local_L1_route_um=distance,source_wire_segment_limit_um=max_segment,local_segments=segments,requested_registered_edges_per_segment=2,local_route_edges=local_edges,forward_route_CDC_PHY_envelope_edges=flight,reverse_route_CDC_PHY_envelope_edges=flight,CDC_edges_per_end=2,PHY_flight_edges=1,CDC_depth_flits_reserved=4,CDC_FIFO_adequacy_and_clock_ratio_qualified=False,source_physical_PG_OBS_pin_escape_lane_availability_qualified=False,full_duplex_directional_tracks=duplex_tracks,source_horizontal_layer='M4',source_horizontal_pitch_um=horizontal_pitch_um,source_M3_vertical_stub_pitch_um=.036,source_wire_segment_bound_is_clock_BUF_domain_not_data_lane_characterization=True,neighbor_port_model_capacity_bound_not_DRC_fit=True,channel_width_with_halfpool_reservation_um=route_width_um,channel_reservation_is_not_available_tracks=True,proposed_port_strip_mm=[32.5,vm_center[1]/1e6-.75,33,vm_center[1]/1e6+.75],source_stage_package_distance_um=None,requested_latency_envelope_not_characterized_pipeline=True),
      timeout=dict(source_default=1024,required_successful_max_edges=required_timeout,default_screen_PASS=1024>=required_timeout,proposed_ACK_TIMEOUT=timeout,proposed_timeout_no_extra_counter_bits=True,retained_RETRY_MAX=2,successful_bound_first_attempt_only=True,arbitrary_stall_or_crc_error_can_fault=True,source_multi_flit_duplicate_ACK_first_flit_behavior_requires_gate=True),
      calendar=dict(domain='source logical edges; target1.2GHz conversion conditional on physical closure',source_origin=10,input_last_visible=input_visible,owner_native_origin=native_origin,shifted_EID0_template_last_root=source_last_root,shifted_EID0_template_owner_idle=source_idle,shifted_template_is_not_remote_expert_runtime=True,final_destination_visible=final_visible,all_delivery_owner_debt_retired=done,packets=timeline,baseline_local_I66_retire=422,extra_critical_path_edges=done-422,extra_critical_path_us_conditional=(done-422)/1200,extra_destination_visibility_edges=final_visible-420,extra_destination_visibility_us_conditional=(final_visible-420)/1200,debt_retirement_is_not_automatically_consumer_critical=True,no_prefetch_no_overlap_case=True,input_ready_edge_assumed_for_this_case=10,owner_identity_ready_assumed_for_this_case=10,actual_source_indexed_owner_response_edge=None,actual_source_input_producer_ready_edge=None,conditional_start_rule='max(actual source indexed owner response, input producer ready); translate entire envelope by supplied accepted origin, never treat unknown as zero',prefetch_lead_needed_to_keep_original_owner_origin_edges=native_origin-10,result_last_visibility_delta_even_if_entire_input_prefetched_edges=final_visible-native_origin-410,required_fulltoken_join='max(producer_ready + finite forward service, owner acceptance) -> native phase -> result visible/consumer demand; ACK debt blocks only actual same-port reuse, not an artificial universal consumer barrier',strictly_positive_intrinsic_source_store_forward_delta_edges=intrinsic_done-422,intrinsic_excludes_real_wire_CDC_PHY_cost=True,six_selected_EIDs_ordered_not_parallel_by_assumption=True,whole_token_delta=None,other1148call_shapes_not_I66_timing_transfer=True,AR_and_six_position_MTP_iteration_drafter_commit_rollback_unbound=True,no_token_loss_proven=False),
      service_bound_contract=dict(reserve_before_GO=['one neighbor credit and RX wholepacket space','5120word VM frame and64word assembly sink','576 tagged nonready roots capture','all finite link/out grants and CDC FIFO allocation'],input_accept_II=1,link_accept_II=1,RX_delivery_accept_II=1,local_destination_commit_edges=1,successful_terminal_bound=done,bound_requires_all_reserved_positive_services=True,actual_service_accepts_measured=False,CRC_function_combinational_not_mapped=True,missing_costs_not_zero=True),
      area=dict(source_endpoint_state_bits=endpoint_bits,TX_state_bits=TX_bits,RX_state_bits=RX_bits,root_capture_added_bits=result_capture_bits,pipeline_FF_bits_per_neighbor_port=pipeline_bits,CDC_positive_state_bits_per_port=CDC_bits,all_FF_floor_mm2_per_port=FF_floor_mm2,CRC_decoder_mux_clock_reset_PG_hold_extra_unpriced=True,port_strip_reservation_mm2=port_strip_mm2,route_corridor_reservation_mm2_per_port=corridor_mm2,port_and_corridor_budget_mm2=per_port_reservation,no_add_FF_floor_on_top_of_containing_slot=True,busiest_owner_two_port_debit_on_hub_shard_mm2=side_addition,global_endpoint_state_bits=endpoint_count*endpoint_bits,old_physical_screen_mm2=physical['area']['screen_mm2'],updated_screen_mm2=whole,remaining_mm2=858-whole,no_containment_credit_against_inherited_services=True,packing_proven=False),
      physical_stalls=dict(accepted_cfg_input_root_WRACK_binding=False,observed_native_edges_are_local_only=True,whole_reticle_screen_is_not_routed_fit=True,link32b_CRC_not_ROM_ECC=True),
      decision='Concrete existing-source provider candidate priced; cannot establish no-token-loss. Reject zero-delay/ACK-free cross-stage adoption. Default1024 timer cannot support the requested spatial envelope; proposed timeout and reserved capture are model-only.',
      next_minimal_gates=['Nash bind runtime accepted indexed owner/command and exact5120word preload/576row root identity to this reserved service','physical neighbor package placement, actual shore pins and link lanes/PHY/CDC service <= requested positive envelope','source endpoint full CRC/delivery/duplicate/sequence/reset gate and contextual SS60/FF25','caller source RESET1/recursive GO screen and actual branch/reset/PG/pin geometry (e0f3) remain separate local blockers'],
      physical_build_admitted=False,full_token_rate_qualified=False,new_jobs=0)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(build(),indent=2,sort_keys=True)+'\n')
