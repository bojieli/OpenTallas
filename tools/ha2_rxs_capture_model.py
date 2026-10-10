"""Pre-build HA2 macro capture collar sizing; independent of routed timing."""
def model():
    w, tags, lanes = 544, 16, 2
    word = w + tags
    return dict(schema="opentallas.uarch.ha2_capture_collar.v1", adopted=False,
        mechanism="One preserved local capture register per used SRAM output; raw_q remains the next transport stage",
        macs_per_cycle=0, compute_intensity=0, communication_bits_per_cycle=lanes*word,
        memory_port_bytes_per_cycle=dict(read=lanes*word/8, write=lanes*word/8),
        replicas=lanes, SRAM_macros=4, capture_register_bits=lanes*word, extra_valid_bits=lanes,
        multiplexer_cost=0, demultiplexer_cost=0, capture_data_fanout=1,
        collar_columns=8, collar_width_um=6.6, collar_height_um=77.76,
        collar_capacity_bits_per_macro=8*int(77.76/0.27), required_max_bits_per_macro=512,
        channel_capacity_tracks=int(77.76/0.096), tracks_needed_max=512,
        die_area_um2=840.024*201.528, macro_area_um2=4*171.288*77.76,
        extra_flop_area_um2=(lanes*word+lanes)*0.2916,
        floorplan_fit=8*int(77.76/0.27)>=512,
        clock_period_ps=833.333, added_latency_cycles_vs_RREG=1,
        added_latency_cycles_vs_original_SRAM_rx=2, added_latency_ns_vs_RREG=0.833333,
        credit_roundtrip_extra_cycles=1, full_rate_credit_depth=8,
        latency_composition="Each traversed HA2 receiver +1 edge vs RREG; no aggregate token credit before measured parent schedule",
        physical_obligations=["TT setup >=0, FF hold >=0, DRC0", "Macro capture flops beside their own rd_out pins", "Credit/deadlock/identity/reset full-shape gate", "No IO or macro timing relaxation"])
