"""Callable sizing for the independent HC quarter gather-clock experiment.

This models the physical envelope only; it has no numeric/token-path adoption
credit. The registered arithmetic lanes and all source-capture clocks stay as C1.
"""
def model(plan, floorplan, period_ps=833.333333):
    groups = plan['groups_per_chain']
    chains = plan['chains']
    lanes = plan['lanes']
    gather_bits = groups * plan['acc_bits_per_chain']
    capture_bits = lanes // chains * plan['lane_out_bits']
    face_bits = plan['WO'] // chains * plan['face_stages']['t_sfu']
    h = floorplan['quarter'][1]
    w = floorplan['quarter'][0]
    channel = floorplan['channel']
    return {
        'scope': 'PHYSICAL ENVELOPE, not numeric HC or a token-path implementation',
        'enable_default': False,
        'clock_mapping': 'south gather clk2, north gather clk6; source/arithmetic clocks unchanged',
        'clock_roots': chains,
        'clock_sinks_per_root': gather_bits + capture_bits + face_bits,
        'gather_clock_spine_um_per_half': h / 2,
        'clock_max_geometric_reach_um_from_quarter_half_root': h / 4 + w / 2,
        'clock_extra_signal_tracks_lower_bound': 2,
        'clock_buffer_area': 'must be measured by CTS; no zero-cost clock claim',
        'clock_insertion_latency': 'CTS measured, not fixed at zero or assumed equal to old banks',
        'macro_output_to_capture_crossings': lanes * plan['lane_out_bits'],
        'macro_capture_budget': 'real pin-registered lane clk-to-Q plus phase/skew and setup/hold; PENDING',
        'face_budget': 'unchanged actual die I/O delays and 60/25ps signoff uncertainty; PENDING qualification',
        'port_boundary_bits': plan['WI'] + plan['WO'],
        'replica_count': lanes,
        'result_bits_per_lane_per_cycle': plan['lane_out_bits'],
        'result_gather_bits_per_cycle': lanes * plan['lane_out_bits'],
        'accumulator_bits_per_cycle': chains * plan['acc_bits_per_chain'],
        'memory_port_bytes_per_cycle': 0,
        'macs_per_cycle': 'unchanged real C1 lanes; quarter mapping is not an arithmetic workload',
        'data_mux_demux_change': 0,
        'additional_data_flops': 0,
        'logical_latency_cycles_added': 0,
        'envelope_gather_chain_cycles': groups + 1 + plan['face_stages']['t_sfu'],
        'envelope_gather_chain_ns': (groups + 1 + plan['face_stages']['t_sfu']) * period_ps / 1000,
        'token_latency_change': '0 logical cycles in envelope; production composition unqualified',
        'outline_um': [w, h],
        'channel_um': channel,
        'signal_tracks_per_layer_at_048um_pitch': int(channel / .048),
        'routing_fit': 'existing data topology; clock buffer/spine competition must be measured',
        'physical_status': 'UNQUALIFIED; TT>=0 FF>=0 DRC0 required, SS sensitivity reported',
        'actual_producer_contract': 'unavailable for this envelope; phase-varied mapping gate is scoped evidence',
    }
