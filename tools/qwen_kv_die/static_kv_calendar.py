#!/usr/bin/env python3
"""Native attention K/V address and static buffer admission model.

Actual rowctl K permutation maps onto physical PC sectors 0..255 in order.
V's n-major order maps onto 512..767 in a different permutation. Four physical
PC sectors form each 1024-bit row. This models the actual 32 groups/128 PCs;
no C++ on-chip memory, latency assumption or dynamic row matcher is admitted.
"""
import argparse
import hashlib
import json
from pathlib import Path

GROUP_ORDER = (4, 5, 0, 1, 2, 3, 6, 7)
CORE_PS = 833.334
HBM_PS = 1024.0


def k_t(index, stack, group):
    idx = group + 8 * index
    pidx = ((idx >> 11) << 11) | (((idx >> 6) & 15) << 7) | (((idx >> 10) & 1) << 6) | (idx & 63)
    return (((pidx >> 7) & 15) << 9) | (stack << 7) | (pidx & 127)


def sector(t, is_v):
    return (int(is_v) << 9) | (((t >> 6) & 1) << 7) | (((t >> 9) & 15) << 3) | ((t >> 3) & 7)


def physical_pc(stack, group, quarter):
    return 32 * stack + 4 * GROUP_ORDER.index(group) + quarter


def model():
    k = {(s,e):[k_t(i,s,e) for i in range(256)] for s in range(4) for e in range(8)}
    v = {(s,e):[] for s in range(4) for e in range(8)}
    for p in range(2):
        for n in range(32):
            for c in range(128):
                t=n*256+p*128+c
                v[(t>>7)&3,t&7].append(t)
    assert sorted(t for ts in k.values() for t in ts)==list(range(8192))
    assert sorted(t for ts in v.values() for t in ts)==list(range(8192))
    assert all([sector(t,False) for t in ts]==list(range(256)) for ts in k.values())
    assert all(sorted(sector(t,True) for t in ts)==list(range(512,768)) for ts in v.values())
    assert len({physical_pc(s,e,q) for s in range(4) for e in range(8) for q in range(4)})==128
    return dict(schema='opentallas.native_static_kv.model.v1',context=8192,groups=32,pseudo_channels=128,
                row_bits=1024,sector_bits=256,sectors_per_row=4,required_k_rows=8192,required_v_rows=8192,
                k_sector_order=list(range(256)),v_first_group_sector_order=[sector(t,True) for t in v[0,0]],
                core_period_ps=CORE_PS,hbm_period_ps=HBM_PS,
                physical_minimum_read_cycles_per_pc=512,
                acquisition_minimum_ps=512*HBM_PS,
                k_burst_core_cycles=256,k_acquisition_minimum_core_cycles=256*HBM_PS/CORE_PS,
                k_minimum_prefill_rows_due_to_frequency=256*(1-CORE_PS/HBM_PS),
                landing_depth=128,landing_sram_bits=128*128*256,landing_sram_bytes=128*128*256//8,
                macro='ot_sram_1r1w_128x256_m1_r2c2',macro_um=[94.824,41.064],
                historical_pc_slot_um=[86.4,172.8],requested_pc_slot_um=[151.2,172.8],minimum_macro_core_channel_um=20,requested_parent_width_um=237.6,
                group_order=list(GROUP_ORDER),native_qualified=False,
                remaining=['actual controller refresh/row-command calendar','V ring lifetime admission','fixed-phase core/HBM CDC return timing','actual 32K/4V consumer composition','128 PC native physical views and measured phi-R','unchanged-price full-token schedule/cost'])


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(model(),indent=1)+'\n')

if __name__=='__main__':main()
