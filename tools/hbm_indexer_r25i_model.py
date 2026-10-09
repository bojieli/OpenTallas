"""Isolated full-shape indexer sizing; imported by the unified model."""
import math

def hbm_indexer_die_interface_model(*, taps=1, relay_stages=24, stacks=4, utilisation=0.55,
                                  key_relay_stages=0, line_fifo_aw=4, score_fifo_aw=6,
                                  scorer_height_um=2800):
    """Prebuild sizing of eb67c5c57 score/selector wrapper; estimates, no closure credit.

    Arithmetic sizing comes from DEDICATED[indexer]. The link latency is a lower
    bound until the connected exact bench measures the complete frame path.
    """
    if taps not in (1, 4) or stacks != 4 or not 0 < utilisation <= 1:
        raise ValueError("qualified indexer geometry is four stacks, one or four taps")
    lanes = 16 // taps
    key_bytes = 68
    rate = 1e12 / 1.2e9
    key_input = 8 * 1099
    score_bits = taps * (38 * lanes + 2)
    macs = 16 * 32 * 128
    lower_link_cycles = 2 * relay_stages + 2
    return dict(
        scope="prebuild estimate; no exactness, physical closure or service bandwidth credit",
        source="physical/hbm_accel_die_views/index/DESIGN.md; eb67c5c57",
        arithmetic=dict(keys_per_stack_cycle=16, slices_NK4_per_stack=4,
            MACs_per_stack_cycle=macs, MACs_per_key_byte=macs/(16*key_bytes),
            compute_issue_cycles_at_2736_keys=math.ceil(2736/16)),
        service=dict(required_keys_per_stack_cycle=rate/key_bytes,
            required_bytes_per_stack_cycle=rate, line_ports_per_stack=8,
            line_payload_bytes=136, provided_bytes_per_stack_cycle=1088,
            contiguous_blocks_per_stack=342, PCs_per_stack=32,
            caveat="kind2 single-PC service must be replaced by admitted striped credit reassembly"),
        boundaries_per_stack=dict(key_input_bits_per_cycle=key_input,
            query_bus_bits=571, score_bits_per_cycle=score_bits,
            input_credit_bits=8, output_credit_bits=taps),
        replication=dict(stacks=stacks, scorer_instances=stacks*taps,
            slices_NK4_per_die=16, selector_instances=1,
            query_fanout_per_slice=32, score_quarter_mux_inputs=4,
            selector_lane_join=taps),
        storage=dict(line_landing_bits_per_stack=8*(2**line_fifo_aw)*1098,
            score_landing_bits_per_die=stacks*taps*(2**score_fifo_aw)*(38*lanes+1),
            added_line_landing_bits_per_stack=8*((2**line_fifo_aw)-16)*1098,
            added_score_landing_bits_per_die=stacks*taps*((2**score_fifo_aw)-64)*(38*lanes+1)),
        flow_control=dict(line_credits=2**line_fifo_aw, score_credits=2**score_fifo_aw,
            key_credit_roundtrip_lower_bound=2*key_relay_stages+2,
            score_credit_roundtrip_lower_bound=2*relay_stages+2,
            sustained_key_lines_per_port_cycle_bound=min(1, (2**line_fifo_aw)/(2*key_relay_stages+2)),
            sustained_score_beats_per_stack_cycle_bound=min(1, (2**score_fifo_aw)/(2*relay_stages+2))),
        floorplan=dict(scorer_cells_um2_estimate_per_stack=3050000,
            scorer_slot_um2_per_stack=2000*scorer_height_um,
            scorer_slot_capacity_um2=2000*scorer_height_um*utilisation,
            extra_FIFO_cell_area_status="unqualified until mapped and routed; original 3.05mm2 estimate excludes added landing storage",
            selector_cells_and_macros_um2_estimate=400000,
            selector_slot_um2_estimate=400000/utilisation,
            utilisation=utilisation,
            routing_track_demand_per_stack=key_input+571+score_bits+8+taps,
            routing_capacity_status="unqualified: requires R25I real pins and global route corridors"),
        latency=dict(relay_stages_one_way=relay_stages,
            key_relay_stages_one_way=key_relay_stages,
            interface_lower_bound_cycles_per_layer=lower_link_cycles,
            interface_lower_bound_cycles_per_token_8_index_layers=8*lower_link_cycles,
            tap_query_extra_hops=3*(taps-1),
            benchmark_required="base exact + MUT_LANE/GID/KEEP/SVAL/QORD; complete frame cycles"))

def hbm_indexer_r25i_physical_model():
    """Full-shape native R25I reservations with credits sized before routing.

    Increase the historical FA4/LA6 queues for real die-distance round trips.
    Area increments below are FF floors; mapped mux/clock costs remain required.
    """
    model = hbm_indexer_die_interface_model(relay_stages=32, key_relay_stages=24,
        line_fifo_aw=6, score_fifo_aw=7, scorer_height_um=3000.24)
    key_extra = 8 * (64 - 16) * 1098
    score_extra = 4 * (128 - 64) * 609
    model.update(default_enabled=False, adopted=False,
        physical_params=dict(L=16, FA=6, CRED=128, T=1, LA=7, MEMV=1, READLAT=2),
        credit_admission=dict(key_one_way_hops=24, key_return_hops=24,
            key_capture_and_return_edges=4, line_credits_per_port=64,
            score_one_way_hops=32, score_return_hops=32,
            score_capture_and_return_edges=4, score_credits_per_stack=128),
        fifo_area_delta_floor_um2=dict(key_per_stack=key_extra * 0.2916,
            score_per_die=score_extra * 0.2916),
        native_slots=dict(score_primary_um=[2000.16, 3000.24],
            score_parallel_fallback_um=[2000.16, 3402.0],
            selector_um=[1399.656, 844.56],
            placement='four side-band scorers; selector above SU-full in the spine'),
        routing_capacity=dict(track_pitch_um=0.048, key_lines_per_stack=8,
            key_tracks=8 * 1099, preferred_key_corridors=dict(
                SM_interrow_lines=5, service_gap_lines=2, hub_edge_lines=1),
            qualification='capacity reservations only; exact station paths and GRT still required'),
        acceptance='full-shape exactness/negative controls plus admitted physical context; no rate credit yet')
    model['storage'].update(line_landing_bits_per_stack=8*64*1098,
                           score_landing_bits_per_die=4*128*609)
    return model
