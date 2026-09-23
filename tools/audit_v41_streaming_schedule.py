#!/usr/bin/env python3
"""Closed-form arithmetic schedule, not workload or RTL simulation."""
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def phase(k, outputs, latency=3, issue_period=3, active_fraction=.65):
    if k % 32 or min(k, outputs, latency) < 1 or issue_period < latency:
        raise ValueError('Requires native blocks and recurrence-safe issue period')
    if not 0 < active_fraction <= 1:
        raise ValueError('Invalid active fraction')
    blocks = k // 32
    # Each group owns L independent output chains and 32 scalar lanes.
    # Lane j computes partial block 32*c+j. Chain s issues at s+t*T.
    groups = math.ceil(outputs / latency)
    chains = min(outputs, latency)
    partial_lanes = groups * 32
    # Blocks arrive in groups of 32 every 32*T cycles. The ordered adder
    # consumes one per chain every T cycles, completing before the next chunk
    # overwrites its ping-pong slot. Tail lanes are disabled.
    first_partial_ready = 31 * issue_period + latency
    finish = first_partial_ready + (blocks - 1) * issue_period + latency + chains - 1
    return {
        'k': k, 'outputs': outputs, 'blocks_per_output': blocks,
        'recurrence_cycles': latency, 'issue_period': issue_period,
        'groups': groups, 'active_scalar_lanes': partial_lanes,
        'active_ordered_adders': groups,
        'provisioned_scalar_lanes_with_spatial_reserve': math.ceil(partial_lanes / active_fraction),
        'provisioned_adders_with_spatial_reserve': math.ceil(groups / active_fraction),
        'arithmetic_cycles': finish,
        'partial_ping_pong_bytes': groups * latency * 32 * 4 * 2,
        'weight_ping_pong_bytes': groups * latency * 32 * 17 * 2,
        'ordered_accumulator_bytes': groups * latency * 4,
        'peak_equivalent_rom_ports_at_65pct_delivery': math.ceil(partial_lanes * 17 / 32 / (256 * .65)),
        'first_partial_ready': first_partial_ready,
    }


def main():
    model = 'configs/models/candidates/deepseek-v4.1-flash.json'
    m = json.loads((ROOT / model).read_text())
    op = m['metadata']['operator_config']
    h, n, e = op['hidden_size'], op['moe_intermediate_size'], m['experts_per_token']
    cases = []
    for latency, period in [(1, 1), (3, 3), (3, 5)]:
        phases = [phase(h, 2*n*e, latency, period), phase(n, h*e, latency, period)]
        cases.append({'latency': latency, 'issue_period': period, 'phases': phases,
                      'layer_arithmetic_cycles': sum(p['arithmetic_cycles'] for p in phases),
                      'expert_arithmetic_us_at_1ghz': sum(p['arithmetic_cycles'] for p in phases)*m['num_layers']/1000,
                      'scope': 'Arithmetic construction with operands ready and independent block semantics; no claim of complete service latency.'})
    out = {'schema': 'opentallas.v41-streaming-schedule.v1', 'cases': cases,
           'status': 'arithmetic_schedule_constructed_physical_and_numerical_feasibility_open',
           'assumptions': ['32 concurrent native partial engines per output chain, interleaved across L chains per scalar lane.',
                           'Separate ordered-add pipeline per chain group. Partial and weight stores are banked per engine/group, not one shared SRAM port.',
                           '65% spatial availability reserves idle engines; it does not cover temporal stalls. The T=5 sensitivity explicitly inserts issue gaps.',
                           'ROM port rate includes 16 payload bytes and one scale byte per native block, amortized through staged chunks.',
                           'Weight ping-pong allocation is capacity only. Initial fill, ROM conflicts and external transport are not included in arithmetic cycles.',
                           'Scale multiplication, activation quantization, SiLU, routing, output conversion, expert merge and all other model operators remain unpriced.'],
           'input_sha256': {p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in (model, 'tools/audit_v41_streaming_schedule.py')}}
    (ROOT/'results/architecture/v41_streaming_schedule.json').write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
    for c in cases:
        print(c['latency'], c['issue_period'], c['layer_arithmetic_cycles'], c['phases'][-1])


if __name__ == '__main__':
    main()
