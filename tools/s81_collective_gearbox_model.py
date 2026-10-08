"""Pre-build sizing of the full-width S81 registered-head gearbox successor."""
import json
from s81_collective_lane_sizing import model as lane_model


def model():
    result = lane_model(345.6)
    result.update(schema='opentallas.s81.collective_gearbox_head.v1',
        predecessor='s81ph-dsfd_coll_lane_e-ac313d866-wide',
        predecessor_ss_ps=-553.14, predecessor_ff_ps=-2.11,
        mechanism='Register FIFO head selection on the preceding queue update; shift from head directly.',
        shape=dict(frame_bits=595, reverse_bits=53, slot_bits=596, gearbox_bits=456,
                   accumulator_bits=1052, fifo_slots=4),
        added_flops_per_lane=595, added_flops_eight_lanes=4760,
        area_allowance_um2_per_lane=1190,
        area_allowance_basis='Conservative 2 um2 per head bit including flop, bypass mux and local buffering; replace with synthesis.',
        estimated_cell_area_um2=67535+1190,
        estimated_utilization=(67535+1190)/(345.6*(340.2-1.08)),
        queue='Four original slots; head mirrors current slot, is not extra capacity. Simultaneous write/read bypass preserves collision semantics.',
        latency=dict(added_cycles=0, token_latency_delta_ns=0, reverse_delta_cycles=0,
                     frame_order='Identical beat-by-beat including empty slots, idle beats and markers.'),
        fifo_ports=dict(write_bits_per_cycle=595, head_prefetch_read_bits_per_cycle=595),
        added_local_wires_bits=595,
        topology='Existing four-way selection now terminates in head flops; 595 head bits feed existing barrel shift. No added global broadcast.',
        timing_risk='Measured sh fanout and mux precede shift. Registration removes their serial composition but shift alone may fail; physical closure is unproven.',
        exactness='Full-width cycle equivalence against immutable original; queue boundaries, overflow, reset and RX re-lock; deliberately broken head selection must fail.',
        opt_in='HEAD_REG=0 default; HEAD_REG=1 candidate only.')
    return result


if __name__ == '__main__':
    print(json.dumps(model(), indent=2))
