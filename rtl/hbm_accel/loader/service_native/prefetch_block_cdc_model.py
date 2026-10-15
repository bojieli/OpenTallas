#!/usr/bin/env python3
"""Cycle model of the first correct, serialized-issue reverse HBM boundary.

This model prices one outstanding request per actual XOR-mapped PC. It does not
claim the peak HBM bandwidth: dense four-sector PC runs serialize response RTT.
"""
import argparse
import json


def pc_of(sector):
    return ((sector >> 2) ^ (sector >> 7) ^ (sector >> 12)) & 31


def run(base, total):
    assert 0 < total <= 2048
    assert (base & ((1 << 30) - 1)) + total <= 1 << 30
    owner = {}; next_ordinal = 0; accepted = 0; cycle = 0
    # Independent bounded PHY RTT; accepted responses arbitrate one per lane.
    while accepted < total:
        used = set()
        for pc, (ordinal, due) in list(owner.items()):
            lane = ordinal & 7
            if due <= cycle and lane not in used:
                used.add(lane); del owner[pc]; accepted += 1
        if next_ordinal < total:
            sector = (base & ((1 << 30)-1)) + next_ordinal
            pc = pc_of(sector)
            if pc not in owner and (cycle + pc) % 5:
                owner[pc] = next_ordinal, cycle + 3 + ((pc + next_ordinal) % 7)
                next_ordinal += 1
        cycle += 1
    return dict(base=base, total=total, hbm_cycles=cycle,
                hbm_ns=cycle * 1.024, fixed_stream_cycles=(total + 7)//8,
                issue_policy='one global ordinal per HBM cycle, one outstanding per PC',
                bandwidth_qualified=False)


def main():
    p=argparse.ArgumentParser(); p.add_argument('--out'); a=p.parse_args()
    receipt=dict(schema='opentallas.prefetch_block_cdc_model.v1',
                 pc_mapping='(s[6:2] ^ s[11:7] ^ s[16:12])',
                 cases=[run(4099,640),run(12295,2048)],
                 dense_eight_pc_histogram={str(pc):sum(pc_of(4096+i)==pc for i in range(8)) for pc in sorted({pc_of(4096+i) for i in range(8)})},
                 qualification_status='mechanism_only_latency_priced')
    text=json.dumps(receipt,indent=2)+'\n'
    if a.out:open(a.out,'w').write(text)
    print(text,end='')


if __name__=='__main__':main()
