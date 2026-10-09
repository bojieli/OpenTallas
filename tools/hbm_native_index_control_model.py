"""Size the missing dynamic HBM index frame controller before RTL build."""

def model():
    descriptor = 73 + 7 + 14 + 10 + 2
    state = 4 + 4 + 2 + 1 + 1
    return dict(schema='opentallas.hbm.native_index_control.v1', default_enabled=False,
        replicas=1, MACs_per_cycle=0, compute_intensity=0,
        memory_bytes_per_cycle=0, communication_intensity='frame metadata and actual keep-mask delivery',
        register_bits=2*descriptor+2*state+2*344,
        boundary_bits_per_cycle=dict(frame=90, keep=345, retained_owner=73,
            query_block_existing=1048, query_credit_existing=1,
            topk_existing=612, candidate_existing=72),
        routing_tracks_required=90+345+73,
        channel_capacity_tracks=None,
        fanout_cost='full73 owner/allocation checks; one frame and keep emitter; no payload replicas',
        multiplexer_cost='dynamic descriptor field packing; no query payload mux',
        cell_area_floor_um2=(2*descriptor+2*state+2*344)*.2916,
        floorplan_slot_fit=False, placement_context='current selected R25I required',
        latency_cycles=dict(descriptor_capture=1, keep_mask_pulses=4,
            keep_mask_min_spacing=5, keep_to_frame_gap=3, frame_to_query_start=4),
        token_latency_basis='one accepted index stage per indexed layer; '
            'keep stages add at least24 control edges before query; publication and '
            'consumer drain are actual dependencies, never overlapped by assumption',
        clocks=dict(period_ps=833.333, setup_uncertainty_ps=60, hold_uncertainty_ps=25),
        mutable_protection='dual-rail descriptor/state; mismatch stops new emission and retains lease',
        source='existing ot_hbm_integrated_native_index_sram_join checked publication and query source',
        dependencies=['actual CP retained73 descriptor', 'actual producer publication ACK and drain',
            'actual four342-bit keep masks with held frame', 'native credit adapter',
            'actual VM/router commit and drain receipts'],
        functional_qualified=False, physical_qualified=False, headline_credit=False)
