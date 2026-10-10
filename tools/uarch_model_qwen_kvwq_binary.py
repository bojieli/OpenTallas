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
