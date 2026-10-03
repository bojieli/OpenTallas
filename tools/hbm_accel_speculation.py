"""Opt-in HA7 sensitivity pricing from saved W19 measurements; no execution."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'results/uarch/hbm_accel_speculation_20261003'
INPUTS = BASE / 'inputs'
REC = INPUTS / 'results/speculative/v41_hbm_speculation_methods_20261003'


def price():
    record = json.loads((REC / 'v41_hbm_speculation_methods.json').read_text())
    union = json.loads((REC / 'router_union.json').read_text())
    assert record['reproduction_gate']['ok']
    assert record['reproduction_gate']['ar_us'] == 442.14
    assert record['reproduction_gate']['verify_p6_w19_union_us'] == 715.82
    draft = record['draft']['measured_union']
    contexts = {}
    for context, data in record['contexts'].items():
        rows = []
        for width in range(2, 7):
            verify = data['verify_by_P'][str(width)]
            # Doubling the exposed fetch term is ONLY a bandwidth sensitivity.
            # It excludes unknown two-stack index/attention/refresh contention.
            penalty = verify['parts_measured_us']['fetch'] + draft['parts_us']['fetch']
            step = verify['measured_union_us'] + draft['total_us']
            tau = {name: values[str(width-1)] for name, values in record['tau_sets'].items()}
            rows.append(dict(width=width, gamma=width-1,
                per_layer_union=union['union_by_p'][str(width)]['per_layer'],
                verify_us=verify['measured_union_us'], draft_us=draft['total_us'],
                sequential_step_us=round(step, 3),
                two_stack_exposed_fetch_only_penalty_us=round(penalty, 3),
                two_stack_sensitivity_step_us=round(step+penalty, 3),
                rates={name: dict(four_stack_tokens_s=round(t*1e6/step, 2),
                    two_stack_fetch_only_tokens_s=round(t*1e6/(step+penalty), 2)) for name,t in tau.items()},
                selectors=dict(concurrent_global_units=width, added_global_units=width-1,
                    distributed_rank_endpoints=96*width, temporal_index_layers=8,
                    baseline_serial_cycles=8*width*419,
                    prospective_parallel_cycles=8*419,
                    prospective_saving_us=round(8*(width-1)*419/1.2e9*1e6, 6),
                    saving_applied=False, area_and_routing_qualified=False)))
        contexts[context] = rows
    return dict(schema='opentallas.ha7.hbm-speculation-pricing.v1',
        enabled_by_default=False, adopted=False, source_commit='d2aff19ef',
        scope='saved measured component composition and explicit sensitivities; no new inference or hardware qualification',
        source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(INPUTS.rglob('*')) if p.is_file()},
        router_trace=union['source'], drafter_stage_union=union['drafter']['union_per_stage'],
        contexts=contexts, overlap_credit_us=0,
        missing_two_stack_terms=['index scan bandwidth and candidate service',
            'attention/KV bandwidth', 'refresh and arbitration interference',
            'mapped expert stripe service and finite source ownership'],
        needed_measured_overlap_join=[
            'source-bound per-layer union with unchanged reduction/selection order',
            'actual shared-expert execution simultaneous with routed W2 fetch, including refresh',
            'retained source/tag/generation and real request, ACK, reverse retirement timestamps',
            'finite activation/result contexts for all verify columns with backpressure',
            'P physical selector replicas with area, routing, fanout and SS/FF qualification',
            'connected completion compared with serialized baseline on identical payloads',
            'draft starts only after accepted bonus token and layers37-39 entering state exist'],
        exclusions=['no DS20 or union SM RTL changes','no inference, P&R or new jobs',
                    'no assumed compute/fetch overlap credited','no full two-stack rate claim'])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--enable-ha7', action='store_true')
    parser.add_argument('--out', type=Path)
    args = parser.parse_args()
    if not args.enable_ha7:
        parser.error('explicit --enable-ha7 required')
    text = json.dumps(price(), indent=2, sort_keys=True)+'\n'
    if args.out:
        args.out.write_text(text)
    else:
        print(text, end='')


if __name__ == '__main__':
    main()
