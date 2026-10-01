#!/usr/bin/env python3
"""Verify FA's W11 attribution against immutable Git blobs; optionally replay estimates.

The scheduling estimates are not RTL measurements. Historical failed RTL records
remain failed, and issue intervals are never labelled per-region unit busy time.
Run --check [--replay-tree /path/to/clean/86e88836/worktree].
"""
import argparse
import collections
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
RECORD = ROOT / 'results/uarch/fusion_audit_w11_run_level.json'


def blob(commit, path):
    return subprocess.check_output(['git', 'show', f'{commit}:{path}'], cwd=ROOT)


def historical(commit):
    rows = {}
    for name in ('f00', 'f2517'):
        base = 'results/rtl/w11_checkpoint_recovery_20261001/'
        r = json.loads(blob(commit, base + name + '.fail.json'))
        trace = json.loads(blob(commit, base + name + '.issues.json'))['runs'][0]
        intervals = collections.Counter()
        prev = 0
        for cycle, pc, unit in trace['issues']:
            assert cycle >= prev
            if unit == 2:
                tag = trace['tags'][pc]
                intervals[tag.split('.', 1)[-1]] += cycle - prev
            prev = cycle
        s = r['single_step']
        assert trace['cycles'] == s['cycles']
        rows[name] = dict(status=r['status'], single_step_pass=s['pass'],
                          engine_parameters=r['engine_parameters'], cycles=s['cycles'],
                          global_su_busy_cycles=s['unit_busy_cycles']['su'],
                          su_issue_attributed_intervals_by_region=dict(sorted(intervals.items())),
                          su_issue_attributed_intervals_total=sum(intervals.values()),
                          per_region_su_busy_cycles=None)
    return rows


def verify(r):
    assert r['schema'] == 'opentallas.fa.w11-run-level.v1'
    assert r['adoption'] is False
    for entry in r['git_sources']:
        assert hashlib.sha256(blob(entry['commit'], entry['path'])).hexdigest() == entry['sha256']
    commit = r['estimate_source_commit']
    for shape, raw in r['estimates'].items():
        assert raw['shape'] == shape
        for path, sha in raw['inputs'].items():
            assert hashlib.sha256(blob(commit, path)).hexdigest() == sha
        for kind in ('unfused', 'fused'):
            x = raw[kind]
            assert x['hidden'] == x['su_cycles_in_order'] - x['su_cycles_interleaved']
            assert x['leg'] == 42 and x['fused_leg'] == 5
    assert r['historical_reduced_rtl'] == historical(r['rtl_evidence_commit'])
    assert all(x['status'] == 'fail' for x in r['historical_reduced_rtl'].values())


def replay(r, tree):
    assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=tree, text=True).strip() == r['estimate_source_commit']
    assert not subprocess.check_output(['git', 'status', '--porcelain', '--untracked-files=no'], cwd=tree)
    checkpoint = tree / r['reduced_checkpoint']['path']
    assert hashlib.sha256(checkpoint.read_bytes()).hexdigest() == r['reduced_checkpoint']['sha256']
    for shape, expected in r['estimates'].items():
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'estimate.json'
            env = dict(os.environ)
            for key in list(env):
                if key.startswith('HDC_') or key == 'OPENTALLAS_BUILD':
                    env.pop(key)
            subprocess.run([sys.executable, 'tools/w11_su_fuse.py', '--shape', shape,
                            '--interleave', '--out', str(out)], cwd=tree, env=env,
                           check=True, stdout=subprocess.DEVNULL)
            assert json.loads(out.read_text()) == expected


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', required=True)
    parser.add_argument('--replay-tree', type=Path)
    args = parser.parse_args()
    r = json.loads(RECORD.read_text())
    verify(r)
    if args.replay_tree:
        replay(r, args.replay_tree)
    print('PASS: committed source pins, scheduling arithmetic, and historical issue attribution')


if __name__ == '__main__':
    main()
