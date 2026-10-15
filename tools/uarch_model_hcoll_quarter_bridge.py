"""Pre-build resource model for a real, compiler-reserved quadrant ring.

No floorplan dimensions or timing credit are invented. Geometry arguments are
mandatory for a wire-latency result; source-to-consumer edge distances include
the destination input capture. The bridge never stores a waiting flit.
"""
import math

RING = (0, 1, 3, 2)

def route(src, dst):
    a, b = RING.index(src), RING.index(dst)
    direction = 1 if (b-a) % 4 <= 2 else -1
    result = [src]
    while result[-1] != dst:
        a = (a + direction) % 4
        result.append(RING[a])
    return result

def model(edge_lengths_um=None, max_wire_segment_um=None, pitch_um=.048):
    npt = (3, 2, 2, 2)
    quarters = []
    for q, n in enumerate(npt):
        ns, nd = n+2, 2*n+2
        # Each output owns its entire input-face register set. No giant root.
        leaf = ns*547 + math.ceil(math.log2(ns)) + 1 + 546 + 2
        quarters.append(dict(qid=q, local_ports=n, sources=ns, outputs=nd,
            router_clock_roots=nd, max_router_root_flops=leaf,
            rx_select_roots=n, rx_select_root_flops=2*547+1+1+546+2,
            total_flops=nd*leaf+n*(2*547+1+1+546+2),
            mux_one_bit_2to1_equivalents=nd*545*(ns-1)+n*545))
    result = dict(status='ANALYTIC_CANDIDATE_UNQUALIFIED', quarter_ring=RING,
        quarters=quarters, macs_per_cycle=0, memory_bytes_per_cycle=0,
        queue_capacity=0, payload_bits=545, lane_bits_with_valid=546,
        ring_edges=4, directions_per_edge=2,
        boundary_bits_per_cycle_per_direction=546,
        data_bytes_per_cycle_per_direction=545/8,
        reserved_slots_per_cycle_per_direction=1,
        total_directed_wire_bits=4*2*546,
        tracks_per_corridor_both_directions=1092,
        minimum_single_layer_width_um=1092*pitch_um,
        channel_available_tracks=None, area_um2=None, floorplan_fit=None,
        rx_mux_to_qslots_added_edge_distance=2,
        router_input_to_next_consumer_edge_distance=2,
        bridge_qslots_source_growth=0, bridge_qslots_output_root_growth=0,
        local_source_binding='existing qslots rail TX outputs',
        local_sink_binding='PHY TX or registered mux replacing existing rail RX input',
        endpoint_tx_edges=5,
        composition='qslots TX -> source router(2) -> relays -> destination router(2) -> endpoint; RX ejection adds RX mux(2) then original qslots',
        graph_candidate='96 ranks circulant +/-1,+/-4,+/-16,+/-24, eight actual ports; compiler evaluates conflicts',
        latency_improvement_claim=None,
        latency_pending='full G96 exact graph calendar; baseline bidirectional ring 3436 vs immutable 1325.9',
        physical_pending=['actual hub coordinates and corridors','relay placement and SS/FF timing','mapped area, clock insertion, congestion'])
    if edge_lengths_um is not None:
        if len(edge_lengths_um) != 4 or max_wire_segment_um is None or max_wire_segment_um <= 0:
            raise ValueError('four actual edge lengths and positive segment bound required')
        segments = [max(1, math.ceil(x/max_wire_segment_um)) for x in edge_lengths_um]
        relays = [s-1 for s in segments]
        result.update(edge_lengths_um=edge_lengths_um,
            wire_segments_per_edge=segments, relay_roots_per_direction=relays,
            relay_flops=sum(relays)*2*546,
            one_edge_source_to_destination_endpoint_capture=[4+r for r in relays],
            two_edge_source_to_destination_endpoint_capture=[6+relays[i]+relays[(i+1)%4] for i in range(4)])
    return result

if __name__ == '__main__':
    import json
    print(json.dumps(model(), indent=2))
