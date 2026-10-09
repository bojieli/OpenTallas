"""HGI COLL decode front; no reduction datapath duplication (HGI-1 G10/G14)."""
def model():
    return dict(status='analytic_before_build_not_qualified', model_scope=['DeepSeek-V4.1 HBM','Qwen3-8B HBM'],
        macs_per_cycle=0, compute_intensity='control decode only; existing 8-input tree performs arithmetic',
        memory_bytes_per_cycle=0, boundary_input_bits=182, boundary_output_bits=82,
        replicas_per_die=1, request_mux_inputs=1, output_demux_outputs=6,
        largest_control_fanout=8, routing_tracks_needed=264,
        routing_channel_capacity=6250, channel_basis='300um channel / 0.048um pitch, one layer; estimate',
        slot_um=[300,160], estimated_cell_area_um2=1800, slot_fit_fraction=1800/48000,
        added_dispatch_cycles=2, added_latency_ns_at_1p2ghz=2/1.2,
        token_latency_cycles_ds_upper_bound=1122, token_latency_cycles_qwen_upper_bound=144,
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

def row_formatter_model(k=2048,row_words=32):
    return dict(status='analytic_before_build',macs_per_cycle=0,replicas_per_die=1,
      compute_intensity='address/control only, no new HBM reader or row storage',
      memory_bytes_per_response=64,request_bits=60,response_bits=513,
      output_bits=560,routing_tracks_needed=1133,routing_channel_capacity=6250,
      channel_basis='300um /0.048um one-layer pitch estimate',slot_um=[600,240],
      area_estimate_um2=12000,area_fraction_estimate=12000/144000,
      mux_inputs=2,max_control_fanout=32,held_payload_register_bits=512,
      owner_block_range=[1,255],selection_count_bits=21,incoming_selected_id_bits=32,context_count_bits=32,context_rows_limit=1048576,group_sizes=[1,2,4,8,96],
      start_capture_validation_cycles=2,ds_B8_fast_mapping_cycles=1,generic_mapping_cycles=41,
      stream_policy='one selected row in flight, one reader word outstanding; retain response under output backpressure',
      added_ds_control_cycles_per_row_upper_bound=3,
      added_ds_token_cycles_upper_bound=8*k*3,
      added_generic_cycles_per_row_upper_bound=43,
      row_words=row_words,rows=k,default_enable=0,
      source_access='existing reader request owner/local_row/word, response written/data; no second indexed reader',
      acceptance='TT>=0 FF>=0 DRC0 exact owner/local/list/payload/written faults plus mutants')
