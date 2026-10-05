#!/usr/bin/env python3
"""Architecture-only latency budgets; deliberately not a candidate TPOT model."""
import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HBM = 'results/rtl/dshbm_1m_allmeasured_20261004/composition.json'
ROM = 'results/rtl/dsrom_1m_allmeasured_20261004/composition.json'
PROGRAM = 'results/rtl/dshbm_baseline_measured_20261004/program.json'


def screen():
    hbm, rom, program = [json.loads((ROOT/p).read_text()) for p in (HBM, ROM, PROGRAM)]
    jobs = sum(op['kind'] == 'mv' for layer in program['layers'] for op in layer['ops'])
    memory = defaultdict(lambda: {'count': 0, 'listed_us': 0.0})
    for row in hbm['path']:
        if row['node'].startswith('hbm:'):
            memory[row['node']]['count'] += 1
            memory[row['node']]['listed_us'] += row['us']
    threshold = rom['AR_us']
    closing = hbm['at_closing_clocks']
    scenarios = []
    for label, baseline, matrix in (
        ('nominal_composition', hbm['AR_us'], hbm['AR_by_term']['sm']),
        ('historical_component_clock_sensitivity', closing['AR_us'], closing['AR_by_term']['sm']),
    ):
        for factor in (1, 2):
            # No memory saving is granted. All mutable service and existing
            # startup charges remain. Doubling is a sensitivity, not a proof
            # that a changed engine count has this precise execution time.
            assumed_base = baseline + (factor-1)*matrix
            margin = threshold-assumed_base
            scenarios.append(dict(reference=label, matrix_service_multiplier=factor,
                reference_us=baseline, matrix_service_us=matrix,
                hypothetical_total_before_new_costs_us=assumed_base,
                allowed_total_new_exposed_cost_us=margin,
                allowed_mean_new_cost_per_raw_matrix_job_ns=margin*1000/jobs,
                candidate_tpot_us=None,
                qualification='Conditional budget only; compute, memory and physical fit unproved'))
    startup = [dict(assumed_added_cycles_per_raw_matrix_job=c,
        assumed_clock_GHz=1.2, all_jobs_unhidden_extra_us=jobs*c/1200)
        for c in (24, 30, 64, 128)]
    paths = (HBM, ROM, PROGRAM, str(Path(__file__).relative_to(ROOT)))
    return dict(schema='opentallas.hbrom.global-headroom.v1',
        status='ARCHITECTURE_ONLY_NOT_AN_ADMISSION_OR_PERFORMANCE_CLAIM',
        current_rom_reference_us=threshold, global_rank_count=program['tp'],
        raw_matrix_jobs=jobs,
        matrix_flush_groups=sum(row['node'].startswith('sm:') for row in hbm['path']),
        memory_path_inventory=dict(memory), scenarios=scenarios,
        startup_sensitivities=startup,
        restrictions=[
            'Preserve authoritative per-operation rank ownership, exact reductions, and collective schedule.',
            '3072 installed row engines are not simultaneously useful for every matrix.',
            'Only expert-fetch and immutable-lookup service can potentially change; do not remove mutable KV service.',
            'Dense HBM weight supply already overlaps compute; no per-matrix HBM-latency subtraction.',
            'Register-file sharing, activation delivery, protection and routing changes need explicit service costs.',
            'Capacity must cover the busiest physical pool, all source archives and auxiliary lookup service.',
            'Neither reference composition establishes contextual physical timing closure.',
            'No RTL, synthesis, simulation or place-and-route is authorized by this screen.'
        ], source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    with args.out.open('x') as f:
        json.dump(screen(), f, indent=2)
        f.write('\n')
