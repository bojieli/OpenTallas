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
        'coherent_limit': 'No analytic positive margin at retained measured data delay; CTS must reduce skew AND hold-repair/wire delay. No guaranteed closure.',
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
