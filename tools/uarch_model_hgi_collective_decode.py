"""HGI COLL decode front; no reduction datapath duplication (HGI-1 G10/G14)."""
def model():
    return dict(status='analytic_before_build_not_qualified', model_scope=['DeepSeek-V4.1 HBM','Qwen3-8B HBM'],
        macs_per_cycle=0, compute_intensity='control decode only; existing 8-input tree performs arithmetic',
        memory_bytes_per_cycle=0, boundary_input_bits=192, boundary_output_bits=104,
        replicas_per_die=1, request_mux_inputs=1, output_demux_outputs=6,
        largest_control_fanout=8, routing_tracks_needed=296,
        routing_channel_capacity=6250, channel_basis='300um channel / 0.048um pitch, one layer; estimate',
        slot_um=[300,160], estimated_cell_area_um2=1800, slot_fit_fraction=1800/48000,
        added_dispatch_cycles=1, added_latency_ns_at_1p2ghz=1/1.2,
        token_latency_cycles_ds_upper_bound=561, token_latency_cycles_qwen_upper_bound=72,
        default_enable=0, numeric_order='backend retains exact rank-order pairwise tree',
        row_mapping='existing gather backend consumes owner block and group; no new row storage',
        group_sizes=[1,2,4,8,96], reserved_rejected=[16,32,64],
        gate='TT>=0 FF>=0 DRC0 plus exact DS lockstep/conformance/mutants; SS sensitivity only')

def endpoint_model():
    # Physical shell from physical/hbm_accel_die_views/coll/view.json; existing
    # NC=8 datapath remains, small groups mask lanes, no extra arithmetic.
    return dict(status='existing_HF5_tree_plus_mode_guard_not_physically_qualified',
        models=['Qwen3-8B HBM','DeepSeek-V4.1 HBM'], replicas_per_die=1,
        macs_per_cycle=0, fp32_adds_per_cycle=112, contributor_columns=8, lanes=16,
        memory_payload_bytes_per_port_cycle=64, network_flit_bits=545,
        network_ports=8, ingress_boundary_bits=4360, egress_boundary_bits=4360,
        reduction_order='rank-order adjacent pairs; depth3 x LAT7',
        group_mux_inputs=4, max_group_mask_fanout=8, reduction_datapath_replicas=1,
        routing_tracks_needed=8720, port_boundary_capacity_bits=8*545,
        routing_capacity_basis='hierarchical core/per-port boundaries retain current PS slot; no flat8680pin launch',
        floorplan_slot='current hfd_coll PS core with8hardenedport leaves, see physical/hbm_accel_die_views/coll',
        additional_area_estimate_um2=40, new_register_bits=0,
        added_data_cycles=0, token_added_cycles_ds=0, token_added_cycles_qwen=0,
        group_sizes=[1,2,4,8,96], rejected_raw_modes=[4,5,6,7,8,9,10,11,12,13,14],
        physical_gate='TT>=0 FF>=0 DRC0; measured macro pin and floorplan fit; SS sensitivity',
        qualification='DS legacy 62run evidence reused; n1/isolation/reservedguard additional exact benches required')
