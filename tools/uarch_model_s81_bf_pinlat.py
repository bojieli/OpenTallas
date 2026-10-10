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


def compact_hierarchy_model():
    """Model true hardened-column locality within the existing reticle width."""
    col_w, front_w, height = 450.144, 100.224, 220.32
    macro_w, macro_h, halo = 125.304, 62.952, 5.4
    column_std = 52977 - 2*macro_w*macro_h
    column_sites = (col_w-4.32)*(height-4.32)-2*(macro_w+2*halo)*(macro_h+2*halo)
    front_std = 8259 + model()['area']['added_latch_area_DFF_body_proxy_um2']
    front_sites = (front_w-4.32)*(height-4.32)
    width = 2*col_w+front_w
    # Invoke the actual generator's slot sizing with this opt-in mixed row.
    # Load a private module so this model does not mutate a caller's die globals.
    import importlib.util
    import sys
    from pathlib import Path
    path = Path(__file__).with_name('dsrom_s81_fulldie.py')
    spec = importlib.util.spec_from_file_location('_bf_compact_geometry', path)
    geo = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = geo
    spec.loader.exec_module(geo)
    rows = []
    for frame_h in (198.72,228.96):
        geo.configure('layer','r8')
        geo.Q_ELEM_FRAME_H=241.92
        geo.BF_PER_REGION=2
        geo.PQ_PLACE=True
        geo.set_pairs(1792)
        slot, capacity = geo.slot_geometry(frame_h,108.)
        rows.append(dict(BF_frame_h_um=frame_h,slot_h_um=slot,slots_per_frame=capacity,
                         frame_h_um=geo.FRAME_H8,die_um=list(geo.DIE),pairs=geo.PAIRS,roots=geo.ROOTS))
    assert width+8.64 <= 1040.256
    assert rows[0]['slots_per_frame']==rows[1]['slots_per_frame']
    return dict(schema='opentallas.s81_bf_compact_hardened.v1',default_off=True,
        adopted=False,physical_qualified=False,
        element='front + two mirrored instances of one hardened column',
        dimensions_um=dict(column=[col_w,height],front=[front_w,height],pair=[width,height]),
        die_reticle_um=[33000,26000],die_outline_delta=0,die_count_delta=0,
        actual_generator_slot_capacity=rows,remaining_capacity='same9slots/frame and1792pairs; no PQrebinning',
        MACs_per_cycle_peak=model()['MACs_per_cycle_peak'],
        memory_ports=model()['memory'],external_bits_delta=0,
        boundary_bits_per_column=776,replicas=dict(columns_per_pair=2,fronts_per_pair=1,pairs_per_die=1792),
        routing=dict(interface_tracks_per_column=776,interface_face_capacity=int(2*height/.064*.7),
                     front_operand_bits=1536,front_top_bottom_capacity=int(2*front_w/.064*.7),
                     hard_column_clock_reset_locality=True,clock_pin='middle of long face',
                     root_crossings='registered abutted boundaries; balanced die tree and contextual FF hold required'),
        replica_cost=dict(two_column_operand_copies=True,front_interfaces=2,
                          one_control_copy_per_column=True,root_ICGs_per_column=18),
        area=dict(column_stdcell_estimate_um2=column_std,column_usable_sites_um2=column_sites,
                  column_util_estimate_pct=100*column_std/column_sites,
                  front_stdcell_estimate_um2=front_std,front_usable_sites_um2=front_sites,
                  front_util_estimate_pct=100*front_std/front_sites,
                  raw_pair_area_um2=width*height,
                  raw_pair_area_delta_pct=100*(width*height/(1002.888*190.08)-1),
                  clock_and_hold_repair_measured_area_pending=True),
        latency=dict(relative_to_flat_QZE_partial_edges=3,relative_to_full948_partial_edges=1,
                     PINLAT_added_edges=0,initiation_interval_unchanged=True,
                     token_price='one extra exposed partial edge vs full948; compose owner token count'),
        exact_gate='full pair HCOL1/PINLAT1 positive transaction oracle plus actual PINLAT and TCG DIFF mutants',
        physical_gate='both hardened masters TT>=0 FF>=0 DRC0, real views and composed contextual boundary timing',
        qualified=False)
