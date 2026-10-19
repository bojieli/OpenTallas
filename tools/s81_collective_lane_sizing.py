"""Measured no-squeeze sizing for the unchanged S81 collective lane RTL."""
import math


def model(width):
    if not math.isfinite(width) or width < 253.8:
        raise ValueError('Width must preserve at least the existing lane area')
    height, cell_area = 340.2, 67535.0
    return dict(
        schema='opentallas.s81.collective_lane_sizing.v1',
        status='CANDIDATE_NOT_ADOPTED',
        evidence=dict(source_commit='a53f40362ba02f64d84edf50a286728f4ab34557',
                      job='s81ph-dsfd_coll_lane_e-a53f40362', host='ot-epyc3',
                      log='routes/s81ph_dsfd_coll_lane_e_a53f40362/work/orfs/logs/asap7/'
                          'opentallas_dsfd_coll_lane_e_asap7_s81ph_s81ph_dsfd_coll_lane_e_a53f40362/base/4_1_cts.log',
                      measured_cell_area_um2=cell_area, measured_utilization_percent=78.5,
                      hold_buffers=17681, grt_overflow=3959),
        lane_um=[width, height], area_um2=width * height,
        estimated_utilization=cell_area / (width * (height - 1.08)),
        utilization_note='Prior measured cell area; CTS/hold buffering may change with footprint.',
        replicas=8, slab_um=[round(2 * width + 507.384 + .192, 4), 1369.416],
        placement_required='Die must reserve the wider slab before adoption; original slot does not fit.',
        macs_per_cycle=0, compute_intensity=0,
        memory_ports=dict(macros_per_lane=10, macro_width_bits=128,
                          max_read_bytes_per_cycle=160, max_write_bytes_per_cycle=160,
                          note='Physical port capacity; unchanged protocol schedule.'),
        boundaries_bits_per_cycle=dict(rx=515, tx=512, core_send=553, core_receive=553),
        routing=dict(pin_pitch_um=.096, lane_core_pins=1113,
                     required_pin_span_um=round(1113 * .096, 4),
                     available_span_um=height - 150.0,
                     local_layers='M2-M7; M8/M9 reserved for die',
                     congestion_closure='PENDING route; no inferred PASS from extra area'),
        replication_cost='Eight existing lanes, same mux/demux/credit/fanout topology; no RTL change.',
        latency=dict(added_cycles=0, token_latency_delta_ns=0,
                     baseline='results/rtl/s81_ph_20261006/collective/bench_v4/summary.txt',
                     ar320_cycles_chb251=709, ar320_delta_vs_w15b=19,
                     condition='Die placement/station changes must be priced separately.'),
        exactness='Identical RTL to pinned v4; existing exact and negative bench records retained.',
        adoption='Requires SS>=15ps, FF>=15ps, DRC0 and die-context STA.')


def storage_p1_model():
    """SRAM landing successor; exact cycle model, prospective physical reserve."""
    width, depth, banks = 553, 8, 5
    outline, band = [561.6, 561.6], [216.0, 246.24]
    std_area = 7357.694940000016
    macro_area = 57120.1845
    band_area = (outline[0] - 4.32) * (band[1] - band[0])
    return dict(
        schema='opentallas.s81.collective_lane_storage_p1.v1',
        status='CANDIDATE_NOT_ADOPTED', opt_in='RXSRAM=1; default0',
        evidence=dict(source_commit='b5c03d49e2805754a8f87b58118bd3c3962fd3ac',
            helper_commit='56d070486',
            sizing_run='ot-epyc6:/srv/opentallas-scratch/claude/ref_gate/dscoll_lane_w_ltr-20261019-084805',
            chip_area_um2=64477.879440, macro_liberty_area_um2=macro_area,
            std_cell_area_um2=std_area,
            geometry='candidate band revision; synthesis measured, placement/CTS unqualified'),
        macs_per_cycle=0, compute_intensity=0,
        storage=dict(logical_bits=width*depth, logical_depth=depth,
            new_macro='ot_sram_1r1w_32x128_m1', banks=banks,
            physical_bits=banks*32*128, unused_bits=banks*32*128-width*depth,
            new_macro_area_um2=banks*51.408*20.79,
            total_lane_macros=15, total_macro_area_um2=macro_area,
            runtime_flop_array_bits=0,
            unconditional_forward_payload_bits=2*width,
            distinct_select_flags=2*math.ceil(width/16)),
        memory_ports=dict(read_bits_per_cycle=width, write_bits_per_cycle=width,
            logical_read_bytes_per_cycle=width/8, logical_write_bytes_per_cycle=width/8,
            physical_new_bank_read_bytes_per_cycle=banks*128/8,
            physical_new_bank_write_bytes_per_cycle=banks*128/8,
            read_pipeline_edges=1, physical_write_registration_edges=1,
            semantics='next-head continuous read, NEW current-write and previous registered-write forwarding'),
        fanout=dict(mapped_local_select_max_loads=32, mapped_shared_hit_max_loads=35,
            qualification='measured synthesis; shared hit35 requires timing/reach review, no payload-enable cone'),
        boundaries_bits_per_cycle=dict(rx=515, tx=512, core_send=553, core_receive=553),
        geometry=dict(outline_um=outline, std_band_y_um=band,
            std_band_area_um2=band_area, std_band_density=std_area/band_area,
            overall_fill=(std_area+macro_area)/(outline[0]*outline[1]),
            macro_origin_x_um=[43.2,259.2,475.2],
            macro_origin_y_um=[43.2,129.6,302.4,388.8,475.2],
            lattice_um=43.2, min_macro_channel_um=41.88,
            actual_parent_fit=False,
            parent_obligation='reserve561.6square and prove actual full-face pin escape; no hidden fit'),
        routing=dict(core_face_signal_bits=1113, min_pin_span_at_6_per_um=1113/6,
            full_face_usable_um=561.6-4.32,
            new_bank_dynamic_signal_pins=128+128+5+5+1+1+1,
            conservative_track_pitch_assumption_um=.096,
            min_channel_track_capacity_one_layer=math.floor(41.88/.096),
            qualification='sizing bound only; verify actual layer pitch/direction and competing nets in route, no route PASS'),
        replication=dict(lanes=8, new_macros=8*banks,
            total_new_macro_area_um2=8*banks*51.408*20.79,
            aggregate_outline_area_um2=8*outline[0]*outline[1],
            mux_cost='two local forward selections per bit; no added runtime arbitration'),
        latency=dict(added_data_edges=0, added_reset_release_edges=0,
            cycle_equivalence_checks=19994, accepted_takes=7113,
            qualification='Verilator5.050 W553/D8 WREG1 WFREE1/2; positive and two forwarding mutants',
            single_user_token_delta_ns=0,
            condition='receiver-only delta; parent relocation, link hops, clock phase and physical latency must be priced separately'),
        adoption='Requires full link positive/mutants, placement/CTS/TT+FF, root PNG review and actual parent fit/escape.')
