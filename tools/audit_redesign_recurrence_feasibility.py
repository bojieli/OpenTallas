#!/usr/bin/env python3
"""Analytical dependency bounds; no RTL implementation or simulation."""
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from opentallas.chip_architecture import qwen_units


def audit(c,m):
    h=m['hidden_size'];meta=m['metadata'];layers=m['num_layers']
    q=meta['num_attention_heads']*meta['head_dim']
    kv=meta['num_key_value_heads']*meta['head_dim']
    attention=2*h*(2*q+2*kv)+2*h+4*meta['head_dim']
    mlp_bytes=m['layer_dense_weight_bytes'][0]-attention-2*h
    assert mlp_bytes%(6*h)==0
    intermediate=mlp_bytes//(6*h)
    vocab=m['resident_only_weight_bytes']//(2*h)
    assert all(x==m['layer_dense_weight_bytes'][0] for x in m['layer_dense_weight_bytes'])
    qwen_units(m)  # independently check checkpoint decomposition
    # Fuse only independent branches: Q/K/V, and gate/up. Successive rows remain
    # dependent even with ideal zero-time attention/nonlinear services between.
    shapes=[('qkv',h,q+2*kv,layers),('attention_output',q,h,layers),
            ('gate_up',h,2*intermediate,layers),('down',intermediate,h,layers),
            ('vocabulary_head',h,vocab,1)]
    lanes=c['dies']*c['clusters_per_die']*c['tiles_per_cluster']*c['lanes_per_tile']
    rows=[]
    for name,k,n,count in shapes:
        rows.append({'operator':name,'K':k,'N':n,'occurrences':count,
                     'independent_output_chains_batch1':n,
                     'ideal_one_cycle_recurrence_floor_cycles':k*count,
                     'max_fraction_of_installed_lanes_with_no_K_split':min(n,lanes)/lanes})
    cycles=sum(r['ideal_one_cycle_recurrence_floor_cycles'] for r in rows)
    floors={str(lat):cycles*lat/c['clock_hz']*1e6 for lat in (1,2,3)}
    linear_budget=c['serial_latency_budgets_us']['linear_weight_and_compute']
    return {'scope':'Single-token whole-K sequential RNE accumulation with at most one dependent update per clock. Outputs are fully parallel, QKV and gate/up fused; attention/nonlinear/memory/control/collective delay omitted. These omissions make this an optimistic lower bound, not predicted TPOT.',
            'intermediate_size':intermediate,'vocabulary_size':vocab,
            'installed_system_lanes':lanes,'operators':rows,
            'linear_dependency_floor_us_by_recurrence_cycles':floors,
            'one_cycle_floor_over_linear_budget':floors['1']/linear_budget,
            'one_cycle_floor_over_85us_target':floors['1']/85,
            'linear_budget_us':linear_budget,
            'required_clock_hz_at_one_update_per_cycle_for_linear_budget':cycles/(linear_budget*1e-6),
            'sequential_contract_meets_linear_budget':floors['1']<=linear_budget,
            'blocked_128_association':'Separate numerical design; available independent K-block work does not prove equivalence to whole-K sequential RNE. No performance accepted pending numerical qualification and exact resource schedule.',
            'decision':'Reject the current 85/75us performance point under unchanged sequential whole-K arithmetic. Keep locality architecture as a candidate; resolve the numerical and dependency contract before implementation.'}


def main():
    cp=ROOT/'configs/architecture/rom_hbm_review_v3.json'
    c=json.loads(cp.read_text());c.update(c['rom_performance_variant'])
    mp=ROOT/c['model'];m=json.loads(mp.read_text())
    result=audit(c,m)
    inputs=[cp,mp,Path(__file__).resolve(),ROOT/'rtl/abi3/ot_a3_lane_pipelined.sv',ROOT/'src/opentallas/chip_architecture.py']
    result['input_sha256']={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}
    out=ROOT/'results/architecture/redesign_recurrence_feasibility.json'
    out.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
