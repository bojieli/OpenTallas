#!/usr/bin/env python3
"""Check full36 parallel-token outputs, traffic volume and measured cycle delta."""
import argparse
import json
from pathlib import Path
import re


def summarize(log):
    done = re.search(r'DONE stages=37 cycles=(\d+)', log)
    if not done:
        raise ValueError('all36 plus head completion missing')
    heads = re.findall(r'HEAD_RANK head die(\d+) next_token=(\d+) next_val=([0-9a-fA-F]+)', log)
    if sorted(heads) != [(str(d), '18', '42282b99') for d in range(4)]:
        raise ValueError('all four exact next-token/logit results required')
    sectors = [0] * 4
    seen = set()
    fills = []
    for stage, rank, cycles, count in re.findall(
            r'MEMSTAT (L\d+|head) die(\d+) fill_cycles=(\d+) fill_sectors=(\d+)', log):
        rank = int(rank)
        if rank not in range(4) or (stage, rank) in seen:
            raise ValueError('duplicate or invalid rank traffic record')
        seen.add((stage, rank))
        sectors[rank] += int(count)
        if stage != 'head':
            fills.append(int(cycles))
    if seen != {(s, d) for s in [*(f'L{i}' for i in range(36)), 'head'] for d in range(4)}:
        raise ValueError('missing stage traffic records')
    if sectors != [36 * 131072] * 4:
        raise ValueError(f'full 576 MiB KV traffic missing: sectors={sectors}')
    cycles = int(done[1])
    return dict(total_cycles=cycles, reference_cycles=193955,
                added_cycles=cycles-193955,
                cycle_ratio_to_reference=cycles/193955,
                accepted_32B_sectors_per_rank=sectors,
                total_kv_bytes=sum(sectors)*32,
                min_fill_cycles=min(fills), max_fill_cycles=max(fills),
                next_token=18, winning_logit_bits='42282b99')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    r = json.loads((a.output/'prepared.json').read_text())
    if not r.get('parallel_transport') or '-GPARALLEL_TRANSPORT=1' not in r['frontend']:
        raise ValueError('actual selected parallel build required')
    terminal = json.loads((a.output/'runtime_terminal.json').read_text())
    if not terminal.get('full_token_pass') or terminal.get('failures'):
        raise ValueError('all layer/KV/head numerical comparisons must pass first')
    metrics = summarize((a.output/'runtime.log').read_text())
    metrics.update(status='PASS_FULLWIDTH_NUMERICAL_AND_TRAFFIC',
                   numerical_checks=len(terminal['output_comparisons']),
                   physical_qualified=False, rate_adopted=False)
    with (a.output/'fullwidth_terminal.json').open('x') as f:
        json.dump(metrics, f, indent=2)
        f.write('\n')
    print(json.dumps(metrics))


if __name__ == '__main__':
    main()
