#!/usr/bin/env python3
"""Pre-build reservation-credit model for the INTERNAL TU/HA2 boundary."""
import json


def model(forward_hops=7, return_hops=7, width=544, injectors=2, depth=64):
    if min(forward_hops, return_hops) < 0 or depth < 2:
        raise ValueError('nonnegative link stages and at least two slots required')
    tag = 16
    queue_bits = injectors * depth * (width + tag)
    # Queue moved from sender edge to receiver; no second wide FIFO added.
    read_muxes = injectors * (width+tag) * (depth-1)
    write_muxes = queue_bits
    pins = injectors * (width+tag+1)
    credits = injectors * (tag+1)
    return dict(default_off=True, adopted=False,
        hierarchy='Internal ot_hbm_accel_tu_endpoint_owner hub issue through HA2 receiver, no new die partial bus',
        clock_GHz=1.2, MACs_per_cycle=0, compute_intensity=0,
        communication_intensity_bits_per_row=width+tag,
        injectors=injectors, remote_slots_per_injector=depth,
        forward_registered_hops=forward_hops, return_registered_hops=return_hops,
        hop_basis='Parametric conservative candidate, not measured pins: no inference of SS closure; 7+7 from1399.656x1403.976um collective Manhattan upper extent /430.56um pitch',
        upstream_hub_cycles=35,
        reservation='Reserve remote slot at hub ISSUE; send consumes actual credit; validated retirement restores both reservation and send credit',
        safety='Arbitrary finite forward/return delay cannot overbook receiver; delayed credit throttles issue',
        identity='Independent16-bit sequential forward and retire IDs per injector; synchronized reset with no old traffic retained; no wrap collision with64 outstanding slots',
        storage_bits=queue_bits, queue_count=injectors,
        removed_sender_queue_bits=injectors*depth*width,
        wide_storage_delta_bits=injectors*depth*tag,
        mux2_inventory=dict(read=read_muxes, write_enable=write_muxes),
        queue_only_area_proxy_um2=queue_bits*.2916+(read_muxes+write_muxes)*(3*.08748+.04374),
        forward_boundary_bits_per_cycle=pins, return_boundary_bits_per_cycle=credits,
        port_bytes_per_cycle=dict(write=injectors*(width+tag)/8,read=injectors*(width+tag)/8),
        local_receiver_to_half_output_register_cycles=1,
        receiver_front_capture_cycles=0,
        forward_sender_capture_cycles=1,
        returned_credit_register_cycles=1,
        unloaded_issue_to_credit_roundtrip_cycles=35+1+forward_hops+1+return_hops+1,
        headroom_for_continuous_half_rate=(depth >= (35+1+forward_hops+1+return_hops+1+1)//2),
        replica_control='Independent reserved and sent counters, forward/return sequence counters and sticky faults',
        area_not_yet_measured=['control', 'relay flops', 'clock/reset tree', 'repair'],
        floorplan_slot_fit=None, routing_tracks_needed=pins+credits,
        channel_capacity=None, physical_closed=False,
        composed_token_latency_cycles=None,
        endpoint_measurement=(dict(
            evidence='results/rtl/ha2_truecredit_endpoint_20261007/63a67fb4c_pass/terminal.json',
            source_commit='63a67fb4c', forward_hops=7, return_hops=7,
            own_rows=384, peer_rows=336, exact_results=24,
            baseline_endpoint_cycles=521, candidate_endpoint_cycles=529,
            measured_increment_cycles=8,
            measured_increment_ns=8/1.2,
            baseline_hub_stalls=92, candidate_hub_stalls=108,
            negative_controls_passed=True,
            scope='Matched one-endpoint calendar only; candidate7+7, not measured placement or whole-token cost')
            if forward_hops==7 and return_hops==7 and width==544 and injectors==2 and depth==64 else None),
        latency_qualification='Protocol sweep measures mechanism; actual pin assignment, hop counts and endpoint composition remain required')


if __name__ == '__main__':
    print(json.dumps(model(), indent=2))
