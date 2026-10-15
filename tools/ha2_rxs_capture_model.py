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


def return_pin_model():
    r=model()
    r.update(schema="opentallas.uarch.ha2_capture_return_pins.v1",
        mechanism=r["mechanism"]+"; separate registered return tag/valid edge and pin-owned input/output flops",
        return_register_bits=34, extra_flop_area_um2=r["extra_flop_area_um2"]+34*.2916,
        added_return_latency_cycles_vs_CAPTURE=1, credit_roundtrip_extra_cycles=2,
        added_send_latency_cycles_vs_RREG=1,
        latency_composition="Send-data path +1 edge vs RREG; return/retirement credit +2 edges vs RREG. Full-shape measured credit depth8 qualification required.")
    return r


def local_transport_model():
    r=return_pin_model()
    r.update(schema='opentallas.uarch.ha2_local_transport.v1',
        mechanism=r['mechanism']+'; existing write registers own every actual SRAM write-pin destination and existing raw registers sit on the capture-to-output transport corridor',
        additional_rtl_registers=0, additional_latency_cycles_vs_CP=0,
        write_pin_owned_flops=1120, mid_transport_flops=1120,
        maximum_write_destinations_per_bit=1,
        write_sink_inventory_required=True,
        west_macro_face_bits_per_cycle=512+256+20,
        east_macro_face_bits_per_cycle=256,
        tracks_needed_max=512+256+20,
        channel_capacity_tracks=int(77.76/.096),
        collar_columns=8,
        placement_obligations=['Inventory every write flop destination across all banks; reject unexpected shared destinations until modeled', 'Use actual transformed macro pin coordinates for R0/MY/MX/R180', 'Anchor1120 write and1120 transport flops before GPL; project blocked midpoints to real free channels with 1um macro clearance; release for DPL legalization', 'No netlist or clock/pin constraint change'])
    assert r['tracks_needed_max'] <= r['channel_capacity_tracks']
    return r
