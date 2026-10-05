#!/usr/bin/env python3
"""Source-bound MTP target sensitivity; no hardware qualification or free overhead."""
import ast
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ACCEPTANCE = 'results/speculative/v41_flash_dspark_onpolicy_greedy.json'
MODEL = 'tools/uarch_model.py'


def committed_tau(walk):
    histogram = walk['histogram_accepted_0_5']
    if len(histogram) != 6 or any(type(n) is not int or n < 0 for n in histogram):
        raise ValueError('six finite accepted-prefix counts required')
    count = sum(histogram)
    if not count or count != walk['n']:
        raise ValueError('iteration count mismatch')
    tau = sum((accepted + 1) * n for accepted, n in enumerate(histogram)) / count
    if abs(tau - walk['tau']) > 1e-12:
        raise ValueError('committed bonus token or walk weighting mismatch')
    return tau


def build():
    acceptance = json.loads((ROOT / ACCEPTANCE).read_text())
    tree = ast.parse((ROOT / MODEL).read_text())
    reference = None
    for node in tree.body:
        if (isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'HBM_W19'
                                                for t in node.targets)):
            reference = {k.arg: ast.literal_eval(k.value) for k in node.value.keywords
                         if k.arg in ('mtp_pass_us', 'drafter_us')}
    if reference is None or set(reference) != {'mtp_pass_us', 'drafter_us'}:
        raise ValueError('explicit reference verify and draft costs required')
    target = 3000
    subtotal = sum(reference.values())
    if subtotal <= 0:
        raise ValueError('positive reference costs required')
    scopes = {'pooled_36_prompts': acceptance['results']['overall']['walk']}
    scopes.update({name: row['walk'] for name, row in acceptance['results']['per_class'].items()})
    rows = {}
    for name, walk in scopes.items():
        tau = committed_tau(walk)
        budget = tau * 1e6 / target
        rows[name] = dict(committed_tokens_per_iteration=tau, iterations=walk['n'],
                          strict_total_iteration_limit_us=budget,
                          reference_draft_verify_subtotal_us=subtotal,
                          reference_remaining_overhead_budget_us=budget-subtotal,
                          conditional_rate_at_zero_additional_overhead=tau*1e6/subtotal,
                          qualified_iteration_us=None, qualified_rate=None)
    return dict(schema='opentallas.ds-mtp-headline-budget.v1',
                status='SOURCE_BOUND_SENSITIVITY_NOT_PERFORMANCE_QUALIFICATION',
                target_committed_tokens_per_second=target, verified_positions=6,
                numerator='accepted draft prefix plus one target token, per actual speculative walk',
                denominator='draft + causal verify + accepted commit/rejected rollback + uncovered control/transport',
                acceptance_checkpoint=acceptance['model'], acceptance_method=acceptance['method'],
                acceptance_contract_transfer_to_exact_deployment_proven=False,
                acceptance_context_transfer_to_1M_proven=False,
                reference_HBM_costs_us=reference, reference_costs_measured_full_iteration=False,
                ROM_current_58stage_PAR2_iteration_us=None,
                missing_overhead_terms=['source-bound commit/rollback visibility',
                                        'uncovered acceptance/control/transport costs'],
                missing_costs_are_zero=False, hardware_admitted=False, workloads=rows,
                input_sha256={p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest()
                              for p in (ACCEPTANCE, MODEL)},
                generator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    with args.output.open('x') as f:
        json.dump(build(), f, indent=2, sort_keys=True)
        f.write('\n')
