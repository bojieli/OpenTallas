#!/usr/bin/env python3
"""Validate optional sparse-attention phase counters and summarize service demand."""
import argparse
import json
from pathlib import Path
import re

PHASES = ['idle', 'index_read', 'index_launch', 'qk', 'denominator', 'av',
          'next_block', 'sink_read', 'epilogue', 'next_head', 'next_row', 'done']


def summarize(text):
    if 'PASS a3_attention_sparse: 9 transactions' not in text or 'FAIL' in text:
        raise ValueError('complete reference-checked nine-transaction campaign required')
    rows = []
    for match in re.finditer(r'PROFILE name=(\S+) total=(\d+) softmax_exp_wait=(\d+) phases=([\d,]+)', text):
        name, total, exp, phases = match.groups()
        total, exp = int(total), int(exp)
        counts = list(map(int, phases.rstrip(',').split(',')))
        if len(counts) != len(PHASES) or sum(counts) != total:
            raise ValueError(f'{name}: phase counts do not reconcile with active cycles')
        if not 0 <= exp <= counts[4] or total <= 0:
            raise ValueError(f'{name}: invalid nested exponential wait')
        rows.append({'name': name, 'active_cycles': total,
                     'phase_cycles': dict(zip(PHASES, counts)),
                     'softmax_exponential_wait_cycles': exp,
                     'softmax_exponential_wait_percent': 100 * exp / total})
    if len(rows) != 9 or len({r['name'] for r in rows}) != 9:
        raise ValueError('nine unique profiles required')
    total = sum(r['active_cycles'] for r in rows)
    exp = sum(r['softmax_exponential_wait_cycles'] for r in rows)
    return {'scope': 'Nine supported sparse-attention reference fixtures; active RTL cycles, not whole-model latency or a measured clock. Exponential wait is nested inside denominator and is not additive. No service replication speedup prediction.',
            'rows': rows, 'aggregate_active_cycles': total,
            'aggregate_phase_cycles': {p: sum(r['phase_cycles'][p] for r in rows) for p in PHASES},
            'aggregate_softmax_exponential_wait_cycles': exp,
            'aggregate_softmax_exponential_wait_percent': 100 * exp / total}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('log', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = summarize(args.log.read_text())
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'rows'}, indent=2))
