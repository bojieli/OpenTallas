"""Full-shape L1 metadata steering, before RTL; no speculative rate credit."""
def model():
    return dict(schema='hbm_expert_steering_r1', sms=32, active_sms=24, experts=6,
        dies=96, rows_per_sm=12, weight_lines_per_sm=288, weight_line_bits=1088,
        macs_per_cycle=0, compute_intensity=0, communication_intensity='metadata only; unchanged packed FP4 payload',
        memory_ports_bytes_per_cycle=0, replica_count=1,
        descriptor_bits=128, descriptor_cycles=24, token_layer_count=40,
        latency_cycles_per_token_upper_bound=40*24,
        weight_boundary_bits_per_cycle=0, result_boundary_bits_per_cycle=90,
        routing_tracks_required=256, routing_channel_capacity='generator must allocate 256 tracks; unqualified',
        mux_demux='six-way expert ID mux, 24-way result counter mux; no weight payload crossbar',
        fanout='registered single descriptor link; sink dispatch to SM is separately integrated',
        state_flops=6*9+24*4+32+8+7+5+9+1+32+32+3+1+12+8,
        area_mm2_assumed=0.01, floorplan_slot_mm2=0.1,
        physical_qualified=False, enabled_by_default=False,
        payload_contract='native flat stream d_base=sm*288, d_lines=288; source expert/matrix/row metadata carried',
        result_contract='job/layer/SM/source expert/matrix/global row checked before forwarding unchanged FP32',
        adoption='exact gate and in-context SS/FF still required; no performance credit')
