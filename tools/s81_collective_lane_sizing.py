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
