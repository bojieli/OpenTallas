#!/usr/bin/env python3
"""Finite-resource necessary bounds and a conservative explicit batch schedule."""
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def projections(hidden=5120, intermediate=2304, selected=6):
    return [(hidden, 2 * intermediate * selected), (intermediate, hidden * selected)]


def screen(lanes, adders, ports, recurrence=1, utilization=.65):
    if min(lanes, adders, ports, recurrence) < 1 or not 0 < utilization <= 1:
        raise ValueError('Positive resources and valid utilization required')
    phases = []
    for k, outputs in projections():
        blocks = k // 32
        macs = k * outputs
        partials = blocks * outputs
        # Packed weights: four payload bits/value and one scale byte/32 values.
        weight_bytes = macs // 2 + partials
        limits = {
            'scalar_mac_service': macs / (lanes * utilization),
            'ordered_partial_add_service': partials / (adders * utilization),
            'packed_weight_service': weight_bytes / (ports * 256 * utilization),
            'native_partial_and_ordered_sum_dependency': (32 + blocks) * recurrence,
        }
        phases.append({'k': k, 'outputs': outputs, 'macs': macs,
                       'partials': partials, 'packed_weight_bytes': weight_bytes,
                       'partial_materialization_bytes': partials * 4,
                       'cycle_bounds': limits, 'necessary_cycles': max(limits.values())})
    return {'scalar_lanes': lanes, 'ordered_adders': adders, 'equivalent_256B_ports': ports,
            'recurrence_cycles': recurrence, 'phases': phases,
            'necessary_layer_cycles': sum(p['necessary_cycles'] for p in phases),
            'necessary_40_layer_us_at_1ghz': sum(p['necessary_cycles'] for p in phases) * .04}


def batch_schedule(outputs_per_wave, recurrence=1):
    """One scalar engine per native partial, one final adder per output.

    Barrier after partial production, then ordered accumulation. Reuse engines
    across waves/projections. Ideal operands and no scale/activation delays.
    This is a constructive arithmetic schedule only, not hardware simulation.
    """
    phases = []
    for k, outputs in projections():
        q = min(outputs_per_wave, outputs)
        blocks = k // 32
        phases.append({'waves': math.ceil(outputs / q),
                       'partial_engines': q * blocks, 'final_adders': q,
                       'partial_storage_bytes': q * blocks * 4,
                       'cycles': math.ceil(outputs / q) * (32 + blocks) * recurrence})
    return {'outputs_per_wave': outputs_per_wave, 'recurrence_cycles': recurrence,
            'phases': phases, 'layer_cycles': sum(p['cycles'] for p in phases),
            'peak_partial_engines': max(p['partial_engines'] for p in phases),
            'peak_final_adders': max(p['final_adders'] for p in phases),
            'peak_partial_storage_bytes': max(p['partial_storage_bytes'] for p in phases)}


def main():
    model_file = 'configs/models/candidates/deepseek-v4.1-flash.json'
    m = json.loads((ROOT / model_file).read_text())
    assert (m['metadata']['operator_config']['hidden_size'], m['metadata']['operator_config']['moe_intermediate_size'], m['experts_per_token']) == (5120, 2304, 6)
    base = screen(1, 1, 1)
    macs = sum(p['macs'] for p in base['phases'])
    partials = sum(p['partials'] for p in base['phases'])
    weight_bytes = sum(p['packed_weight_bytes'] for p in base['phases'])
    assert weight_bytes == m['routed_weight_bytes'] // m['num_layers'] // m['num_experts'] * m['experts_per_token']
    out = {
        'schema': 'opentallas.v41-partial-resources.v1',
        'status': 'finite_resource_screen_not_accepted_implementation',
        'assumptions': {'clock_hz': 1e9, 'utilization_cap': .65, 'layer_budget_cycles': 1000,
                        'native_block': 32, 'scalar_products_per_lane_update': 1},
        'per_layer': {'macs': macs, 'partials': partials, 'packed_weight_bytes': weight_bytes,
                      'partial_leaf_bytes': partials * 4,
                      'minimum_scalar_lanes_average': math.ceil(macs / 650),
                      'minimum_ordered_adders_average': math.ceil(partials / 650),
                      'minimum_equivalent_ports_average': math.ceil(weight_bytes / (650 * 256))},
        'screens': [screen(p, a, ports, recurrence=l) for ports in (678, 1024) for l in (1, 3)
                    for p in (131072, 262144, 524288) for a in (4096, 8192, 16384)],
        'barrier_batch_schedules': [batch_schedule(q, l) for l in (1, 3) for q in (2048, 8192, 16384, 32768)],
        'limits': [
            'Sums gate/up and down phase bounds with whole-producer dependency; gate/up and selected experts parallel.',
            'Passing necessary bounds does not establish a realizable schedule or prove utilization.',
            'Ordered adds must be assigned to enough independent output chains to hide recurrence.',
            'Leaf bytes are producer output traffic; SRAM writes plus reads can double it. Streaming may avoid full materialization.',
            'No g4 numerical equivalence is assumed. Scalar service requirements replace the earlier conditional g4 lane estimate for this candidate.',
            'Barrier schedule omits memory, scales, activation and pipelines; it is an arithmetic construction, not a full latency upper bound.',
            'No area density is borrowed from the differently structured Qwen tile. Macro, lane, accumulator, wiring and power area remain unqualified.',
        ],
        'input_sha256': {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in (model_file, 'tools/audit_v41_partial_resources.py')},
    }
    (ROOT / 'results/architecture/v41_partial_resources.json').write_text(json.dumps(out, indent=2, sort_keys=True) + '\n')
    print(json.dumps(out['per_layer'], indent=2))
    for r in out['screens']:
        if r['scalar_lanes'] == 524288 and r['ordered_adders'] == 16384:
            print(r['recurrence_cycles'], r['necessary_layer_cycles'])
    for r in out['barrier_batch_schedules']:
        print(r['outputs_per_wave'], r['recurrence_cycles'], r['layer_cycles'], r['peak_partial_engines'])


if __name__ == '__main__':
    main()
