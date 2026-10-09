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
