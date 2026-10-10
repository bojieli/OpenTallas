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
        'token_latency_change': '0 added pipeline stages; phase-sensitive edge alignment and production composition unqualified',
        'outline_um': [w, h],
        'channel_um': channel,
        'signal_tracks_per_layer_at_048um_pitch': int(channel / .048),
        'routing_fit': 'existing data topology; clock buffer/spine competition must be measured',
        'physical_status': 'UNQUALIFIED; TT>=0 FF>=0 DRC0 required, SS sensitivity reported',
        'actual_producer_contract': 'unavailable for this envelope; phase-varied mapping gate is scoped evidence',
    }


def compare_registered_cut(plan, floorplan, bank_clocks, period_ps=833.333333):
    """W16 comparison, measured C1 path retained without pretending CTS is known.

    A cut register alone does not authorize multicycle timing. Two-edge margin
    below is conditional on a real hold/enable transport and frame alignment.
    """
    spine = model(plan, floorplan, period_ps)
    transitions = [sum(a != b for a, b in zip(c, c[1:])) for c in bank_clocks]
    crossing_count = sum(transitions)
    data_ps = 1846.64 - 1062.32
    setup_ps = 16.37
    uncertainty_ps = 60
    return {
        'authority': 'W16 compare coherent roots against registered gather cuts before route selection',
        'measured_basis': 'C1 79315a431 existing CTS max path acc_0_8[471] to acc_0_7[471], estimated parasitics, TT overlay',
        'measured_launch_to_D_ps': data_ps,
        'measured_route_period_ps': 770,
        'measured_route_setup_uncertainty_ps': 123,
        'measured_path_launch_minus_capture_clock_ps': 1062.32 - (1531.51 - 770),
        'measured_worst_setup_skew_summary_ps': 1382.72 - 713.24,
        'signoff_uncertainty_ps': {'setup': 60, 'hold': 25},
        'design_margin_ps': 15,
        'coherent_spine': spine,
        'coherent_zero_skew_margin_with_measured_data_ps': period_ps - data_ps - setup_ps - uncertainty_ps,
        'coherent_required_data_delay_for_15ps_margin_ps': period_ps - setup_ps - uncertainty_ps - 15,
        'coherent_limit': 'This budget assumes zero gather skew at the chosen period. Real CTS skew, hold-repair/wire delay and macro capture are still unqualified; no guaranteed closure.',
        'plain_one_edge_limiter_cut': {
            'location': '512-bit relay between acc_0_8 and acc_0_7, not cuts at every bank',
            'relay_clock': 'existing source root clk0; acc_0_7 retains clk1. No clock exceptions.',
            'relay_data_FF': plan['acc_bits_per_chain'],
            'downstream_same_frame_lane_alignment_FF': 8 * 4 * plan['lane_out_bits'],
            'other_half_output_alignment_FF': plan['acc_bits_per_chain'],
            'total_extra_FF_lower_bound': 512 + 8 * 4 * plan['lane_out_bits'] + 512,
            'paired_north_south_cut_extra_FF_lower_bound': 2 * (512 + 8 * 4 * plan['lane_out_bits']),
            'added_full_frame_cycles': 1,
            'added_full_frame_ns': period_ps / 1000,
            'added_FF_area_lower_bound_um2': (512 + 8 * 4 * plan['lane_out_bits'] + 512) * .2916,
            'paired_added_FF_area_lower_bound_um2': 2 * (512 + 8 * 4 * plan['lane_out_bits']) * .2916,
            'FF_area_basis': 'actual ORFS SEQ_RVT_TT220123 DFFHQNx1 0.2916um2; libsha256 57a0b403485b99ebd676942af4673ac086b86c7c75fbdc3e5c0038501dd22ba3',
            'extra_boundary_signals': 0,
            'extra_local_payload_tracks': 512,
            'clock_fanout_increase_lower_bound': 2112,
            'steady_rate_fraction': 1,
            'data_split_example_each_leg_ps': data_ps / 2,
            'example_second_leg_margin_with_retained_path_skew_ps': period_ps - data_ps / 2 - (1062.32 - (1531.51 - 770)) - setup_ps - uncertainty_ps,
            'example_limit': 'Equal split is analytical, not a measurement; each leg includes a new clk-to-Q and actual placement RC. Required +15ps margin on both real legs, including hold.',
            'golden_alignment': 'Delay all 34-bit lane outputs (data/valid/fault) entering groups7..0 of south chain by one edge; delay opposite half final512b by one edge. Mirrored cut delays both half downstream contributions instead of padding one head.',
            'other_paths': 'Other bank crossings and macro capture paths remain. Plain limiter cut may not be sufficient for whole-quarter closure.',
            'native_frame_contract': 'unavailable; this describes mathematical full-frame alignment only, not a qualified native producer or arithmetic stream proof',
            'RTL_status': 'not written; compare against preserved coherent candidate before selection',
        },
        'registered_cuts': {
            'bank_clocks_by_chain': bank_clocks,
            'crossings_by_chain': transitions,
            'cut_registers': crossing_count * plan['acc_bits_per_chain'],
            'added_cycles_per_chain_lower_bound': transitions,
            'added_chain_ns_lower_bound': [n * period_ps / 1000 for n in transitions],
            'additional_data_tracks_per_crossing': plan['acc_bits_per_chain'],
            'cut_register_area': '3072 real mapped FF minimum; area from actual library required before RTL selection',
            'clock_fanout_increase': crossing_count * plan['acc_bits_per_chain'],
            'ordinary_one_edge_cut': 'Each leg remains single-cycle; no guaranteed margin from register count alone. Actual placement and inherited skew must be budgeted.',
            'two_edge_budget_margin_at_retained_path_ps': -454.51 + (period_ps - 770) + (123 - 60) + period_ps,
            'two_edge_transport_requirement': 'A real registered hold/enable captures on the second edge, producer held stable, and all same-frame lane partials delayed together. Not implemented or supplied by current folded envelope.',
            'two_edge_steady_rate_upper_bound_fraction': .5,
            'single_extra_edge_claim': 'Three bank crossings per half, so minimum +3 chain edges; +1 total is unsupported for this topology.',
            'native_frame_and_lane_alignment': 'unbound; extra FIFO/alignment state cannot be omitted from a production model',
            'hold_margin': 'actual FF capture checks still required; setup slack does not prove hold',
        },
        'selection': 'No production selection or route authorization from this comparison. Coherent candidate gate preserved; source review must choose experiment with explicit remaining budgets.',
        'token_composition': 'Neither physical envelope has a native token/frame producer; no token-rate gain credit.',
    }
