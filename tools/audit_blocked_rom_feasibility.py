#!/usr/bin/env python3
"""Static work/dependency bounds for blocked ROM; no workload or RTL simulation."""
import hashlib
import json
from math import ceil, log2
from pathlib import Path
import struct
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tools.audit_redesign_recurrence_feasibility import audit


def f32(x):
    return struct.unpack('!f',struct.pack('!f',x))[0]


def rounding_witness():
    # Exact BF16 products: 4096*4096, 1*1, -4096*4096.
    # Place the first in block 0 and the last two in block 1; all others zero.
    sequential=f32(f32(float(2**24)+1)-2**24)
    blocked=f32(float(2**24)+f32(1-float(2**24)))
    assert sequential==0 and blocked==1
    return {'block_size':128,'K':256,'nonzero_products':{'0':2**24,'128':1,'129':-2**24},
            'whole_K_sequential_result':sequential,'blocked_pairwise_result':blocked,
            'reason':'2^24 + 1 is a binary32 tie rounded to 2^24; 1 - 2^24 is exactly representable. All products are exactly realizable by finite BF16 operands. Zero padding leaves both recurrences unchanged.'}


def bounds(c,m,block=128):
    assert block>0
    base=audit(c,m);lanes=base['installed_system_lanes'];hz=c['clock_hz']
    rows=[]
    for op in base['operators']:
        k,n,count=op['K'],op['N'],op['occurrences']
        blocks=ceil(k/block)
        work=k*n
        # Both are lower bounds. Recurrence is the longest block's chain;
        # total lane work is charged even when interleaving hides recurrence.
        recurrence=min(k,block)
        rows.append(dict(op,blocks_per_output=blocks,independent_block_chains=n*blocks,
                         products_per_occurrence=work,partial_bytes_per_occurrence=4*n*blocks,
                         reduction_adds_per_occurrence=n*(blocks-1),
                         tree_levels=ceil(log2(blocks)),
                         floors_cycles={str(L):max(ceil(work/lanes),recurrence*L) for L in [1,2,3]}))
    floor={str(L):sum(r['floors_cycles'][str(L)]*r['occurrences'] for r in rows)/hz*1e6 for L in [1,2,3]}
    derated={str(L):sum(max(ceil(r['products_per_occurrence']/(lanes*c['mac_utilization_target'])),min(r['K'],block)*L)*r['occurrences'] for r in rows)/hz*1e6 for L in [1,2,3]}
    # Do not add work and latency of the reduction: overlap remains unproved.
    adds=sum(r['reduction_adds_per_occurrence']*r['occurrences'] for r in rows)
    partials=sum(r['partial_bytes_per_occurrence']*r['occurrences'] for r in rows)
    budget=c['serial_latency_budgets_us']['linear_weight_and_compute']*1e-6
    return {'K_block':block,'operators':rows,'ideal_compute_dependency_floor_us':floor,
            'floor_us_with_configured_utilization_cap':derated,'linear_budget_us':budget*1e6,'partial_bytes_per_token':partials,
            'reduction_adds_per_token':adds,
            'minimum_partial_delivery_bytes_per_cycle_system':partials/(budget*hz),
            'minimum_reduction_adds_per_cycle_system':adds/(budget*hz),
            'excluded':'reduction latency/placement, local access conflicts, launch/drain, scalar functions, attention, communications. Sum uses producer-complete operator dependencies.',
            'decision':'Necessary bounds only; non-equivalent arithmetic and unresolved mapped service prevent feasibility acceptance.'}


def main():
    cp=ROOT/'configs/architecture/rom_hbm_review_v3.json';c=json.loads(cp.read_text());c.update(c['rom_performance_variant'])
    mp=ROOT/c['model'];m=json.loads(mp.read_text())
    out={'schema':'opentallas.blocked-rom-feasibility.v1','numerical_counterexample':rounding_witness(),
         'block_sweep':[bounds(c,m,b) for b in [32,64,128,256]],
         'qualified_numerical_contract':False,'architecture_feasible':False,
         'next_gate':'Assess numerical acceptance policy and mapped bank/reduction schedule before RTL or workload simulation. A separate blocked contract must not be presented as sequential-bit-equivalent.'}
    paths=[cp,mp,Path(__file__).resolve(),ROOT/'tools/audit_redesign_recurrence_feasibility.py',ROOT/'rtl/abi3/ot_a3_tree_endpoint_fp32.sv',ROOT/'configs/hardware/abi3_capability/rom_qwen3.json']
    out['input_sha256']={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    (ROOT/'results/architecture/blocked_rom_feasibility.json').write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
    for row in out['block_sweep']:
        print(row['K_block'], row['ideal_compute_dependency_floor_us'],row['minimum_reduction_adds_per_cycle_system'],row['minimum_partial_delivery_bytes_per_cycle_system'])

if __name__=='__main__':main()
