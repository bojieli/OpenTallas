#!/usr/bin/env python3
"""Derive routed-expert traffic from pinned geometry, without a TPOT target."""
import hashlib
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]


def inventory(hidden, intermediate, selected, layers):
    weights = 3 * hidden * intermediate
    assert hidden % 32 == intermediate % 32 == 0
    packed = weights // 2
    scales = weights // 32
    return {'weights_per_expert': weights, 'fp4_payload_bytes_per_expert': packed,
            'e8m0_scale_bytes_per_expert': scales,
            'bytes_per_expert': packed + scales,
            'routed_bytes_per_layer': (packed + scales) * selected,
            'routed_bytes_per_token': (packed + scales) * selected * layers,
            'routed_ops_per_token': 2 * weights * selected * layers}


def rates(inv, expert_budget_us):
    if expert_budget_us <= 0:
        raise ValueError('Expert service budget must be positive')
    return {'expert_budget_us': expert_budget_us,
            'aggregate_local_weight_TB_s': inv['routed_bytes_per_token'] / expert_budget_us / 1e6,
            'routed_arithmetic_TOP_s': inv['routed_ops_per_token'] / expert_budget_us / 1e6}


def main():
    sources = ['compiler/models/deepseek-v4.1-flash/inference_config.json',
               'configs/models/candidates/deepseek-v4.1-flash.json',
               'tools/audit_v41_budget_sensitivity.py']
    config, model = [json.loads((ROOT / p).read_text()) for p in sources[:2]]
    inv = inventory(config['dim'], config['moe_inter_dim'], config['n_activated_experts'], config['n_layers'])
    assert inv['bytes_per_expert'] * config['n_routed_experts'] * config['n_layers'] == model['routed_weight_bytes']
    out = {'schema': 'opentallas.v41-budget-sensitivity.v1', 'inventory': inv,
           'status': 'no_token_latency_target_selected',
           'expert_budget_sweep': [rates(inv, t) for t in (40, 100, 250, 500, 1000, 5000, 10000)],
           'scope': 'Batch-one ordinary decode. Six routed experts per layer, 40 layers, one packed read per selected weight. Shared expert, dense operators, attention, Engram and other service excluded. Rates are internal aggregate service, not an external-link requirement.',
           'previous_112_8_TB_s_origin': '100us token probe with 40us allocated to routed experts, not a user requirement or intrinsic model bandwidth.',
           'input_sha256': {p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in sources}}
    (ROOT/'results/architecture/v41_budget_sensitivity.json').write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
    print(json.dumps(out,indent=2))


if __name__ == '__main__':
    main()
