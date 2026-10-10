"""Size the exact full-rate TCG/BXST2/FXST2/PINLAT successor before RTL.

The combination retains 948dc49b1's arithmetic and tile clocks, and adds the
fada135e4 pin-data lockups. Neither combination closure nor reticle shrink is
credited before measured physical qualification.
"""
def model():
    pin_data = dict(xs_p=8, xs_b=3, xs_sv=2, xs_q0=256, xs_e0=10,
                    xs_q1=256, xs_e1=10, xs_pos=3, xb_pos=3,
                    xb_b=3, xb_sv=4, xb_u=32, xb_d=1024)
    bits = sum(pin_data.values())
    slot = (1002.888, 190.08)
    usable = 145342.231168
    # DFF body proxy is conservative for a latch; actual mapped inventory gates
    # the final area claim. CTS/hold repair is separately measured after route.
    proxy = bits * 0.2916
    base_std = 71300 + 2000  # bf-arch characterization + full input relay estimate
    return dict(schema='opentallas.s81_bf_tcg_pinlat.v1', default_off=True,
        adopted=False, physical_qualified=False, targets=['DeepSeek-V4.1 ROM'],
        source_baselines=dict(full='948dc49b1117040aae4ba7c98c9eda2016e2a5cf',
                              pinlat='fada135e4'),
        parameters=dict(RECUT=2, QZE=1, TCG=1, BXST=2, FXST=2, PINLAT=1,
                        HALF=0, HCOL=0),
        MACs_per_cycle_peak=dict(FP4=128, FP8=64, BF16=32),
        added_MACs_per_cycle=0,
        compute_intensity_MACs_per_ROM_byte=dict(FP4=128/68.5,FP8=64/68.5,BF16=32/68.5),
        memory=dict(installed_macros=4, rows_per_macro=4096, bits_per_macro_word=274,
                    active_macros_per_issue=2, ROM_bytes_per_issue_cycle=68.5,
                    installed_raw_port_bytes_per_cycle=137,
                    new_ports=0, new_bytes_per_cycle=0, ECC=False),
        communication=dict(added_external_bits_per_cycle=0,
                            input_BF_payload_bits=1024, input_FP_payload_bits=512,
                            output_partial_bits=2*63,
                            producer_consumer_flow_control='unchanged finite x FIFO and original issue schedule'),
        replicas=dict(elements_per_layer_die=1792, columns_per_element=2,
                      BF_lanes_per_column=16, tile_ICGs_per_element=37,
                      latch_bits_per_element=bits),
        mux_demux_fanout=dict(new_data_mux_inputs=0, new_demuxes=0,
                             pin_register_to_lockup_fanout=1,
                             lockup_output_fanout='inherits original consumer, no new broadcast',
                             new_pin_clock_sinks_per_element=bits),
        routing=dict(new_external_tracks=0, local_lockup_data_tracks=bits,
                     lockup_data_must_remain_at_pin_register=True,
                     gross_pin_face_capacity_tracks=int(1002.888/.064*.7),
                     local_clock_root_crossings='low-level lockups; pin regs and lockups share spatial CTS group',
                     internal_lane_skew='TCG retained; full routing still measures gated-to-gated carry hops'),
        area=dict(slot_um=list(slot), slot_um2=slot[0]*slot[1],
                  usable_stdcell_site_area_um2=usable,
                  full_stdcell_area_estimate_um2=base_std,
                  added_latch_area_DFF_body_proxy_um2=proxy,
                  utilization_estimate_pct=100*(base_std+proxy)/usable,
                  headroom_at_55pct_um2=.55*usable-base_std-proxy,
                  added_die_latch_area_proxy_mm2=1792*proxy/1e6,
                  actual_latch_CTS_and_hold_inventory_pending=True,
                  outline_and_die_count_delta=0),
        latency=dict(relative_to_full_added_cycles=0,
                     relative_to_flat_QZE_partial_added_cycles=2,
                     full_rate_initiation_interval_unchanged=True,
                     lockup_clock_half_cycle_ps=dict(stream_1p2=833.333/2, serial_0p9=1111.111/2),
                     serial_token_contribution='retain +2 edges for every exposed full partial; PINLAT adds zero edges',
                     frequency_effect='900 MHz BF work takes 4/3 of 1.2 GHz BF work; no speculative token credit'),
        compact_hierarchy=dict(existing_column_um=[520.128,190.08],front_um=[280.152,190.08],
            existing_die_um=[39358,26000],reticle_um=[33000,26000],
            pair_synthesized_cell_area_um2=2*52977+8259,
            original_pair_raw_util_pct=100*(2*52977+8259)/(slot[0]*slot[1]),
            qualified=False,
            next_legal_capacity_candidate='8 columns/half: 1344 pairs/die, +33% layer dies; PQ r128 re-binning required',
            compact_route_admitted=False),
        exact_gate='full pair transaction scoreboard positive plus PINLAT/TCG/XST/FXST/DP/RECUT negatives',
        physical_gate='TT setup >=0, FF hold >=0, DRC0; unchanged signoff and own routed-insertion re-STA',
        qualification='model sizing only; no measured closure or adoption credit')
