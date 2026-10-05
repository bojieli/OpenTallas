#!/usr/bin/env python3
"""Check historical W11 evidence and emit bounded issue-trace calibration.

This does not run RTL, modify the model, or qualify adoption. Issue attribution
includes waits and is distinct from unit busy counters. Sources are Git blobs.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'results/rtl/w11_hub_recovery_20261001'


def read(path):
    return json.loads((ROOT / path).read_text())


def attribution(record, trace):
    run = trace['runs'][0]
    assert record['status'] == 'fail', 'retain overall failed verdict'
    step = record['single_step']
    assert step['pass'] and step['fault'] == 0
    assert step['cycles'] == run['cycles']
    assert all(step[k] == 0 for k in ('logit_mismatches', 'vector_memory_mismatches', 'kv_cache_mismatches'))
    prev, regions = 0, Counter()
    for cycle, pc, unit in run['issues']:
        assert prev <= cycle <= run['cycles']
        if unit == 2:
            regions[run['tags'][pc].split('.', 1)[-1]] += cycle - prev
        prev = cycle
    return dict(cycles=step['cycles'], global_su_busy_cycles=step['unit_busy_cycles']['su'],
                issue_attributed_intervals=dict(sorted(regions.items())),
                issue_attributed_intervals_total=sum(regions.values()),
                per_region_su_busy_cycles=None, overall_status=record['status'])


def check():
    handoff = json.loads((BASE / 'handoff.json').read_text())
    assert handoff['adoption'] is False
    for pin in handoff['git_sources']:
        data = subprocess.check_output(['git', 'show', pin['commit'] + ':' + pin['path']], cwd=ROOT)
        assert hashlib.sha256(data).hexdigest() == pin['sha256']
        assert data == (BASE / pin['archive']).read_bytes()
    rotate = json.loads((BASE / 'rotate_m5.physical.json').read_text())
    assert rotate['status'] == 'pass'
    assert rotate['design']['clock_uncertainty_ns'] == 0.06
    assert rotate['design']['clock_uncertainty_hold_ns'] == 0.025
    assert rotate['target_clock_period_ns'] == 1.111
    assert rotate['place_and_route']['floorplan']['routing_layers'] == ['M2', 'M5']
    assert rotate['place_and_route']['signal_integrity_constraints']['hold_corners'] == ['WC', 'BC']
    report = (BASE / 'rotate_m5.6_finish.rpt').read_text()
    assert 'Corner: WC' in report and 'Corner: BC' in report
    ckv = json.loads((BASE / 'ckv_service.json').read_text())
    for path, sha in ckv['source_sha256'].items():
        data = subprocess.check_output(['git', 'show', ckv['git_head'] + ':' + path], cwd=ROOT)
        assert hashlib.sha256(data).hexdigest() == sha
    assert ckv['status'] == 'pass'
    assert all(r['pass_'] and r['row_errors'] == r['fmt_errors'] == 0 and r['own_row_write_exact'] for r in ckv['runs'])
    files = dict(unfused=('results/rtl/w11_controller_recovery_20261001/u2517.json',
                         'results/rtl/w11_controller_recovery_20261001/u2517.issues.json'),
                 fused=('results/rtl/w11_checkpoint_recovery_20261001/f2517.fail.json',
                        'results/rtl/w11_checkpoint_recovery_20261001/f2517.issues.json'))
    records = {k: read(paths[0]) for k, paths in files.items()}
    u, f = records['unfused'], records['fused']
    assert u['engine_parameters'] == f['engine_parameters']
    for key in ('subcast', 'suret', 'verilator', 'sources_sha256'):
        assert u['operator_fusion'][key] == f['operator_fusion'][key]
    assert not u['operator_fusion']['fused_program'] and f['operator_fusion']['fused_program']
    for key in ('position', 'token', 'next_token'):
        assert u['single_step'][key] == f['single_step'][key]
    inputs = {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for pair in files.values() for p in pair}
    rows = {k: attribution(records[k], read(pair[1])) for k, pair in files.items()}
    saved = rows['unfused']['cycles'] - rows['fused']['cycles']
    wired = read('results/rtl/w11_controller_recovery_20261001/unfused_wired_handoff.json')
    assert wired['su_issue_attributed_intervals_total'] == rows['unfused']['issue_attributed_intervals_total']
    assert wired['su_issue_attributed_intervals_by_region'] == rows['unfused']['issue_attributed_intervals']
    assert wired['comparison']['saved_cycles'] == saved
    for name, sha in wired['evidence_sha256'].items():
        assert hashlib.sha256((ROOT / 'results/rtl/w11_controller_recovery_20261001' / name).read_bytes()).hexdigest() == sha
    terminal = read('results/rtl/w11_terminal_recovery_20261001/handoff.json')
    for name, sha in terminal['evidence_sha256'].items():
        assert hashlib.sha256((ROOT / 'results/rtl/w11_terminal_recovery_20261001' / name).read_bytes()).hexdigest() == sha
    assert terminal['softplus']['status'] == 'not_met'
    assert terminal['rotate_square_small']['status'] == 'failed_build'
    return dict(schema='opentallas.w11-hub-calibration.v1', adoption=False,
                scope='Historical reduced SUN16/SUM8 token at position 7, BCAST25/RET17; not full-shape or interleaving qualification.',
                definition='Each SU issue minus preceding issue charged to current tag, including waits; not per-region busy time.',
                input_sha256=inputs, configurations=rows, saved_cycles=saved,
                fraction_of_unfused=saved / rows['unfused']['cycles'],
                blocked_gates=['strict overall lint', 'KR SS/FF closure in context', 'main-current full-shape exactness', 'composed model adoption gate'])


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out', type=Path)
    args = ap.parse_args()
    result = check()
    if args.out:
        args.out.write_text(json.dumps(result, indent=2) + '\n')
    print(f"PASS historical evidence: {result['saved_cycles']} saved cycles; adoption remains false")


if __name__ == '__main__':
    main()
