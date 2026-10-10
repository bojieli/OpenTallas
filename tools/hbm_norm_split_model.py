"""Analytical sizing for the inherited N64 norm partition, without adoption credit."""
import math


def model(group_lanes=8, group_width_um=None, group_height_um=None,
          exposed_y_calls_per_token=None, exposed_q_calls_per_token=None, channel_um=72):
    if group_lanes not in (8, 16):
        raise ValueError('Only the implemented G8/G16 masters are supported')
    if (group_width_um is None) != (group_height_um is None):
        raise ValueError('Width and height must come from the same view')
    n, d, frequency_ghz = 64, 5120, 1.2
    replicas = n // group_lanes
    chunks = group_lanes // 8
    width = group_width_um or (440 if group_lanes == 8 else 540)
    height = group_height_um or (440 if group_lanes == 8 else 540)
    if width <= 0 or height <= 0:
        raise ValueError('Group dimensions must be positive')
    for calls in (exposed_y_calls_per_token, exposed_q_calls_per_token):
        if calls is not None and (calls < 0 or int(calls) != calls):
            raise ValueError('Exposed invocation counts must be nonnegative integers')
    # One group port list includes pin flops for the 4-copy HC input,
    # gain input, reduction partial, normalized stream, and scalar broadcast.
    group_input_bits = 5 * group_lanes * 32 + 128 + 8 + 32 + 4
    group_output_bits = group_lanes * 32 + 32 + 16 + 3
    group_pin_register_bits = group_input_bits + group_output_bits + 1
    if channel_um <= 0:
        raise ValueError('Channel width must be positive')
    capacity = int(channel_um * 4 / .08)
    required = group_input_bits + group_output_bits
    cols, rows = replicas // 2, 2
    die_width = cols * (width + channel_um) + 60
    die_height = rows * (height + channel_um) + 240
    added_cycles = None
    if exposed_y_calls_per_token is not None and exposed_q_calls_per_token is not None:
        added_cycles = exposed_y_calls_per_token + 2 * exposed_q_calls_per_token
    return dict(
        schema='opentallas.uarch.hbm_norm_split.v1',
        process_order=dict(model_before_inherited_build=False,
            classification='RETROSPECTIVE_MODEL_GAP',
            inherited_source_commit='26f2e4ed219675d4cc71eea046a9c9de483d250a'),
        scope='One DeepSeek HBM N64 D5120 MEM1 HC1 QUANT1 partitioned norm engine',
        adopted=False, enabled_default=False, headline_rate_credit=0,
        other_design_deltas=dict(Qwen_ROM=0, DeepSeek_ROM=0, Qwen_HBM=0),
        shape=dict(lanes=n, elements=d, vectors=d//n, group_lanes=group_lanes,
            group_replicas=replicas, SRAMs_per_group=2*chunks, SRAMs_total=16,
            top_tree_levels=int(math.log2(replicas)),
            group_tree_levels=int(math.log2(chunks))),
        compute=dict(MACs_per_cycle=0, rounded_FP32_ops_peak=11*n-1,
            arithmetic_delta_ops=0, group_hc_multiply=4*group_lanes,
            group_hc_add=3*group_lanes, group_square_multiply=group_lanes,
            group_scale_multiply=2*group_lanes,
            group_partial_tree_add=chunks-1, top_partial_tree_add=replicas-1,
            FP32_ops_per_internal_memory_byte=(11*n-1)/(4*n*4),
            arithmetic='Golden multiply/add rounding and aligned subtree association retained'),
        memory_ports_bytes_per_cycle=dict(X_read=4*n,X_write=4*n,
            gain_read=4*n,gain_write=4*n,per_macro_read=32,per_macro_write=32),
        communication=dict(HC_input_bytes_per_cycle=4*n*4,
            gain_input_bytes_per_cycle=n*4, normalized_bytes_per_cycle=n*4,
            per_group_reduction_bytes_per_cycle=4,
            broadcast_payload_bytes_per_cycle=4,
            replicated_broadcast_wire_bytes_per_cycle=4*replicas,
            memory_bytes_per_normalized_element=16),
        boundary_bits_per_cycle=dict(per_group_input_payload_and_control=group_input_bits,
            per_group_output_payload_and_control=group_output_bits,
            all_group_boundaries=replicas*required,
            clocks_and_reset_per_group=2),
        replica_cost=dict(group_pin_register_bits=group_pin_register_bits,
            total_group_pin_register_bits=replicas*group_pin_register_bits,
            scope='Absolute group interface registers, not a delta against flat engine',
            shared_scalar_control_fanout=replicas,
            lane_data_demultiplexer='Static lane slice wiring; no dynamic mux',
            reduction_mux='Fixed golden tree; no arbitration',
            gain_address_fanout_per_group=chunks,
            SRAM_logical_bits=2*n*(d//n)*32, SRAM_physical_bits=16*128*256),
        routing=dict(channel_width_um=channel_um,assumed_signal_layers=4,pitch_um=.08,
            group_boundary_tracks_required=required,
            channel_capacity_tracks=capacity, analytical_channel_fits=required<=capacity,
            minimum_channel_width_um=required*.08/4,
            actual_channel_and_pin_access_verified=False,
            basis='Conservative simultaneous pin-bit tracks; dedicated channels assumed'),
        area=dict(group_width_um=width,group_height_um=height,
            group_dimension_basis='routed view supplied by caller' if group_width_um is not None else 'inherited route dimensions; not a hardened view',
            group_slot_um2=width*height, replicated_slots_um2=replicas*width*height,
            top_die_um=[die_width,die_height],top_die_um2=die_width*die_height,
            flat_die_um2=1104**2,die_area_ratio=die_width*die_height/1104**2,
            top_logic_band_um=180,outer_ring_total_um=60, channel_um=channel_um,
            measured_total_cell_um2=None,floorplan_slot_fit=None,
            power_delta_W=None,energy_delta_J_per_token=None,
            die_count_delta=None, limitation='Die outline, placement, clock, pin access and power await physical evidence'),
        latency=dict(candidate_clock_GHz=frequency_ghz,
            group_result_and_top_capture_hops=2, removed_RW_stages=2,
            top_broadcast_and_group_capture_hops=2, removed_BW_stages=2,
            reduction_broadcast_loop_delta_cycles=0,
            rstd_delta_cycles=1,y_delta_cycles=1,quant_delta_cycles=2,
            rstd_y_delta_ns=1/frequency_ghz,quant_delta_ns=2/frequency_ghz,
            throughput_delta_vectors_per_cycle=0,
            exposed_y_calls_per_token=exposed_y_calls_per_token,
            exposed_q_calls_per_token=exposed_q_calls_per_token,
            token_delta_cycles=added_cycles,
            token_delta_ns=None if added_cycles is None else added_cycles/frequency_ghz,
            composition='Count only nonoverlapping exposed invocations; q delta already includes y delta',
            limitation='Global invocation calendar must supply exposed counts before rate publication'),
        qualification=dict(SS_setup=False,FF_hold=False,DRC0=False,
            physical_closed=False,die_context=False,model_ready_for_adoption=False))
