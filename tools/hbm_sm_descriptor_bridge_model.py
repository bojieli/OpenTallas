#!/usr/bin/env python3
"""Pre-build finite descriptor transport with actual consumed acknowledgement."""
import json,math

def model(hops=32,depth=2):
 if hops<0 or depth<1:raise ValueError('invalid finite channel')
 cw=max(1,math.ceil(math.log2(depth+1)));aw=max(1,math.ceil(math.log2(depth)))
 chan=58*hops+56*depth+2*cw+2*aw
 south=2*(56*depth+cw+2*aw)
 total=2*chan+4*hops+3
 return dict(status='candidate_not_adopted',protocol='one parent descriptor outstanding, retained until returned actual south d_valid&&d_ready acceptance; finite credit is not delivery acknowledgement',
    payload_bits=56,physical_forward_bits=114,physical_reverse_bits=6,physical_bidirectional_tracks=120,forward_valid_bits=1,internal_credit_return_bits=1,consumed_ack_return_bits=1,sticky_SM_fault_return_bits=1,
    hops_each_way=hops,queue_depth=depth,replicas=32,protected_copies=2,
    total_register_bits=total,flop_only_um2=total*.2916,
    south_queue_state_bits=south,south_queue_flop_only_um2=south*.2916,
    proposed_south_bay_um=[128,64],south_cell_budget_at55pct_um2=128*64*.55,
    earliest_owner_ack_edges=2*hops+2,added_vs_same_cycle_accept_edges=2*hops+2,
    fault_return_added_edges=hops,
    protection='duplicated forward queues, credits, consumption ACK and fault-return chains; compare valid payloads/credits/ACK/fault; complementary pending rails and sticky abort',
    physical_route='Illustrative32hops, not final assignment. Initial obstacle-aware26/32 paths measured3.956-5.016mm with16-31 chain registers under300um bend segmentation; sixpathsblocked. Owner/adapter flight pins and independent dual-rail packing remain unqualified.',
    track_payload_each_copy=56,peak_descriptor_B_per_fast_edge=7,
    conservation='no second source send while pending; owner completion waits actual south acceptance + registered return, independent of route latency',
    open_gates=['actual legal hop count','independent mapped state bank preservation','south bay cell fit and SS/FF','production parent integration'],selected=False)
if __name__=='__main__':print(json.dumps(model(),indent=2))
