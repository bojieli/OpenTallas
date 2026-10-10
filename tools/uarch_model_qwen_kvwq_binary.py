"""Binary lane feed for the posted Qwen KV write control tile (model before RTL)."""
from __future__ import annotations


def model(qd=4, stacks=4, relay_forward=14, relay_return=13):
    if qd != 4:
        raise ValueError('qualification vehicle uses the full four-row queue')
    row_bits = 1024
    groups = 4
    pcs = 32
    queue_bits = qd * (row_bits + 22)
    # Exact successor keeps the physical 8-bit port, emits binary in low three
    # and constants in high five. The old one-hot decoder and off-tile OR4s go.
    ff_delta_per_ctl = -groups * 5
    return dict(schema='opentallas.qwen-kv-write-binary-feed.v1', default_off=True,
        adopted=False, model_precedes_rtl=True,
        models=['Qwen3-8B ROM companion KV die'], stacks_per_die=stacks,
        replicas=dict(controller=stacks, leaf=stacks*pcs, standalone_encoder=0),
        macs_per_cycle=0, compute_intensity_macs_per_byte=0,
        communication_intensity_bits_per_posted_row=4*(256+24+3+9+1)+8,
        memory_ports=[dict(name='posted_row_queue', depth=qd, storage_bits=queue_bits,
                           write_bytes_per_cycle=(row_bits+22)/8, read_bytes_per_cycle=(row_bits+22)/8)],
        boundary_bits_per_cycle=dict(posted_row=1048, physical_feed_per_group=298,
                                     chain_feed_per_group=293, done_per_group=2,
                                     cdc_write_per_pc=290, cdc_return_per_pc=11),
        routing=dict(controller_feed_tracks=4*298+8,
                     controller_two_layer_face_capacity=int(2*518.4/.096),
                     leaf_chain_tracks=293+2, leaf_cdc_tracks=301,
                     leaf_two_layer_vertical_capacity=int(2*183.6/.096),
                     physical_high5_lane_bits='constant-zero pins retained, not routed to leaf',
                     final_segment_target_um=100, SS_reach_sensitivity_um=504),
        replica_cost=dict(read_mux='4:1 x1024 row and 4:1 x22 identity, unchanged',
                          write_demux='4 queue entries, unchanged', feed_data_mux='four fixed256-bit row slices, unchanged',
                          lane_mux='3 bits per group from row identity; old8-bit one-hot removed',
                          lane_fanout=4, quarter_valid_fanout=1, cdc_handshake_fanout=1),
        area=dict(controller_slot_um=[172.8,518.4], leaf_slot_um=[86.4,183.6],
                  control_storage_bits=queue_bits, controller_ff_delta=ff_delta_per_ctl,
                  analytical_ff_area_delta_um2=ff_delta_per_ctl*.2916,
                  removed_standalone_encoder_or2_equivalent=144,
                  removed_encoder_reserved_mm2=16*43.2*43.2/1e6,
                  measured_successor_cell_area_um2=None,
                  slot_fit='reuse closed ctl outline; synthesis/floorplan measures actual utilization'),
        latency=dict(feed_hop_edges=2, done_hop_edges=1,
                     max_leaf_hops=7, max_feed_chain_edges=14, max_done_chain_edges=7,
                     relay_forward_edges=relay_forward, relay_return_edges=relay_return,
                     posted_row_overhead_edges_vs_abutted_leaf=relay_forward+relay_return+21,
                     added_controller_edges=0, single_user_token_added_edges=0,
                     token_overlap_credit='none claimed; posted writes can backpressure if credits exhaust',
                     steady_state='one row in flight per quarter; actual retire period must come from component trace'),
        exact_contract='Same sector bytes/address/tag/durable identity, binary low3 selects t[2:0]; four sectors per row',
        qualification=dict(physical='TT setup>=0, FF hold>=0, DRC0 under unchanged1.2GHz/60ps/25ps and die budgets',
                           exact='full32PC ctl+leaves+CDC+KVW2 path, representative rows, lane/address/data mutants',
                           pinned_default='old ctl RTL and closed views byte-identical',
                           adoption='exact gate and physical record plus closed-view pin/context mapping'))


def leaf_s_model():
    """Physical leaf variant: write pins S, then MX below the CDC S face."""
    return dict(schema='opentallas.qwen-kv-write-leaf-s.v1', model_precedes_pnr=True,
        adopted=False, macs_per_cycle=0, compute_intensity_macs_per_byte=0,
        replicas=128, slot_um=[86.4,183.6], slot_area_mm2=128*86.4*183.6/1e6,
        rtl='unchanged ot_qkvd_kv_wq_leaf; lane strap and registered hops unchanged',
        memory_ports_bytes_per_cycle=0, held_sector_bits=256+24+9,
        boundary_bits_per_cycle=dict(feed_in=293, feed_out=293, done_in=2, done_out=2,
                                     CDC_write=290, CDC_return=11),
        routing=dict(S_pins=293+2+290+11, S_two_layer_capacity=int(2*86.4/.096),
                     N_pins=293+2, E_pins=5, S_density_estimate=596/(2*86.4),
                     CDC_source_pin_x_span=[77.484,106.284],
                     placement='MX immediately below183.72-square CDC; leaf centre aligns CDC S write bundle',
                     final_segment_target_um=100, SS_reach_sensitivity_um=504),
        mux_demux_fanout=dict(lane_compare_bits=3, sector_head_depth=1, CDC_handshake_fanout=1),
        area_delta_vs_old_leaf_um2=0, added_cycles=0,
        floorplan=dict(edge_routing_channel_um=129.6, total_die_height_delta_um=259.2,
                       reason='room for real relay frames around full-height landing columns',
                       area_delta='actual die width times259.2um, recorded by generator'),
        fit='same full183.6-high leaf RTL; route measures cell area and utilization',
        qualification='own optionB TT>=0 FF>=0 DRC0; exact unchanged component; real LEF pin-to-pin reach and mirror legality')


def head_pipeline_model():
    """Capture selected queue row before the four pin-feed banks."""
    d=model(relay_forward=42, relay_return=41)
    d['floorplan']=dict(die_um=[8543.232,24587.28], die_mm2=210.055, edge_channel_um=129.6, control_relay_strip_um=518.832, overlaps=0, outside=0, inherited_landing_far_side=4)
    d['schema']='opentallas.qwen-kv-write-binary-head-pipeline.v1'
    d['area'].update(controller_slot_um=[216.0,648.0], extra_head_state_bits=1024+22+2+1,
                     extra_analytical_DFF_area_um2=(1024+22+2+1)*.2916,
                     reserved_controller_area_delta_mm2=4*(216*648-172.8*518.4)/1e6)
    d['latency'].update(added_controller_edges=1, stage='queue read mux -> selected-row register -> output pin flops',
                        single_user_token_added_edges=0, posted_write_cost='one extra core edge a launched row; full component measures phase/credit effects')
    d['routing'].update(controller_two_layer_face_capacity=int(2*648/.096),
                        selected_row_internal_bits_per_cycle=1049,
                        controller_feed_density_estimate=(4*298+8)/(2*648))
    d['replica_cost']['head_capture_fanout']='one selected-row register per bit, feeds one quarter bank'
    d['qualification']['exact']='full32PC HEAD_PIPE1 component and mutants, same physical298/293-bit feed contract'
    return d


def leaf_s_wide_model():
    """Spend50% more leaf area and write-face length; height fits actual CDC gap."""
    d=leaf_s_model()
    d['schema']='opentallas.qwen-kv-write-leaf-s-wide.v1'
    d['slot_um']=[129.6,183.6]
    d['slot_area_mm2']=128*129.6*183.6/1e6
    d['routing'].update(S_two_layer_capacity=int(2*129.6/.096), S_density_estimate=596/(2*129.6))
    d['routing']['placement']='MX below183.72-square CDC;129.6um S write face aligns CDC S write bundle, height183.6 fits378um pitch'
    d['area_delta_vs_old_leaf_um2']=(129.6-86.4)*183.6
    return d


def mirror_legal_pin_model():
    """Single preferred-direction layer per face avoids incompatible flip residues."""
    return dict(schema='opentallas.qwen-kv-mirror-pin-plan.v1', model_precedes_pnr=True, adopted=False,
        macs_per_cycle=0, compute_intensity_macs_per_byte=0, memory_ports_bytes_per_cycle=0,
        replicas=dict(leaf=128,controller=4), boundary_bits_per_cycle=dict(leaf_S=596,leaf_N=295,leaf_E=5,controller_E=1200,controller_W=1048),
        routing=dict(leaf_horizontal_layer='M4',leaf_vertical_layer='M5',pitch_um=.048,
                     controller_pin_plan='existing head successor retained; actual MY origin gate pending',
                     leaf_S_tracks=int(129.6/.048),controller_E_tracks=int(648/.048),
                     leaf_S_density_bits_per_um=596/129.6,controller_E_density_bits_per_um=1200/648,
                     removed_pair_reason='M4/M5 flipped origin24 modulo48 conflicts with M6/M7 origin32 modulo64, independent of outline'),
        area=dict(leaf_slot_um=[129.6,183.6],controller_slot_um=[216,648],die_mm2=210.055,cell_area_change=0),
        latency=dict(added_edges_vs_wide_leaf=0,controller_head_edges=1,posted_relay_forward_edges=42,posted_relay_return_edges=41),
        replica_mux_demux_fanout='same exact RTL, registers and logical boundary bus ownership',
        qualification='own optionB closure; actual LEF on-track origin, mirror access and composed timing required; no existing job/view overwritten')
