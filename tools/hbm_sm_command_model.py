#!/usr/bin/env python3
"""Conservative native PQ command ingress; model before RTL, candidate only."""
import argparse
import json
import math

def model(hops=8, depth=1, replicas=32):
    if hops < 0 or depth < 1: raise ValueError('nonnegative hops and positive depth required')
    cw=max(1, math.ceil(math.log2(depth+1)))
    aw=max(1, math.ceil(math.log2(depth)))
    bits=47 + 3 + 49*hops + 47*depth + 2*cw + 2*aw
    return dict(status='candidate_not_adopted', instruction='existing seq.hex ten little-indexed 32-bit words',
        op_payload_bits=47, forward_bits=48, return_credit_bits=1, die_control_bits=111,
        die_control_down_bits=106, die_control_up_bits=5, replicas=replicas,
        command_ingress_bits=320, command_ingress_bytes=40, MACs_per_cycle=0,
        channel_payload_bytes_per_cycle=47/8, channel_forward_hops=hops,
        channel_return_hops=hops, queue_depth=depth, channel_first_accept_edges=hops+1,
        channel_credit_round_trip_edges=2*hops+2,
        full_rate_depth=2*hops+2, channel_peak_commands_per_cycle=min(1,depth/(2*hops+2)),
        producer_policy='one outstanding op until real retirement; operand publication required before send',
        producer_extra_edges_before_transport=1,
        successor_latency='per op: publication wait + 1 ingress edge + forward hops + 1 FIFO edge; next issue waits actual retire',
        modeled_flop_bits_per_replica=bits, flop_only_area_um2_per_replica=bits*.2916,
        flop_only_slot_um2_at_55pct=bits*.2916/.55,
        area_scope='lower bound; mux/control and physical pin station area not measured',
        tracks_per_replica=49, track_capacity=None, slot_fit=None,
        open_gates=['loader/program-memory record producer', 'operand publication and actual retire binding',
                    'actual control path hop census', 'crossing/clock/reset binding', 'mutable control-state protection', 'SS/FF and full geometry'],
        selected=False)
if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--hops',type=int,default=8); p.add_argument('--depth',type=int,default=1)
    a=p.parse_args(); print(json.dumps(model(a.hops,a.depth),indent=2))
