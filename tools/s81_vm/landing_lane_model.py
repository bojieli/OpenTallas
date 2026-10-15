#!/usr/bin/env python3
"""Pre-build physical/microarchitecture model for four independently rooted landing lanes.
A candidate only; source and routed evidence must qualify each lane before parent adoption.
"""
import json

def model():
    side = 95.04
    lanes = []
    for lane in range(4):
        # Every crossing is a local pin register; two payload stages, 14-bit row counter/output.
        # RTL bit count; mapped bound also reserves118 clones for pin-register splitting.
        flops = 1024 + 19 + 1 + 1 + 15 + 14 + 3 + 5
        # One crossing per data bit; M2+M4 horizontal or M3+M5 vertical at .048um tracks.
        # Conservative 50% track reserve for clocks/PG/local routing.
        capacity = 2 * (side - 8.64) / .048 * .5
        demand = 512 + 23
        lanes.append(dict(lane=lane, outline_um=[side, side], area_mm2=side*side/1e6,
            clock_roots=1, rtl_register_bits=flops, mapped_flop_upper_bound=1200, payload_bits_per_edge=512,
            control_bits_per_edge=23, output_bits_per_edge=530, boundary_bits_per_edge=1065,
            memory_bytes_per_edge=0, macs_per_edge=0, route_cut_demand=demand,
            route_cut_capacity=capacity, route_cut_ratio=demand/capacity,
            landing_age_edges=2, startup_release_edges=4, added_normal_edges=0))
    return dict(schema='opentallas.s81.landing_lane_model.v1', status='CANDIDATE_NOT_ADOPTED',
        cause='r5 final FF rst_n pin capture clock 236.22ps versus input reference179.18ps; local leaf86.56ps; FF-1.405ps',
        lanes=lanes, lane_replica_count=4, payload_mux_count=0, payload_demux_count=0,
        control_replication=4, arm_control_fanout=4, reset_fanout=4,
        area_per_slice_mm2=sum(x['area_mm2'] for x in lanes),
        area_four_slices_mm2=4*sum(x['area_mm2'] for x in lanes),
        previous_area_per_slice_mm2=.18144**2, clock_roots_four_slices=16,
        previous_clock_roots_four_slices=4, roots_added=12,
        candidate_arrangement_um=[2*side,2*side],
        parent_slot_budget_mm2=14.0, parent_slot_max_um=[3369.6,4150],
        slot_change='4x95.04um independent lane leaves per slice replacing181.44um monolith; +12 landing root pins total; parent placement/clock ABI pending',
        single_user_latency_change_edges=0, initiation_interval_edges=1,
        normal_rows_per_edge=4, normal_payload_bytes_per_edge=256,
        full_parent_fit='UNPROVEN: total640-leaf VM area owned by area stream; this candidate must be composed there')

if __name__ == '__main__':
    print(json.dumps(model(),indent=2))
