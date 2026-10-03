#!/usr/bin/env python3
"""Collect the existing DSpark head1/head4 terminal jobs; never launch a model.

--wait waits without a deadline for both runner exit files. Output is exclusive:
previous pass/failure evidence is never overwritten. A failed runner lacking a
JSON result still produces a failure record with its exit code and logs.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import time


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def validate(result, oracle, positions, source_root):
    errors = []
    if result.get('status') != 'pass' or result.get('source_stable') is not True:
        errors.append('runner did not pass with stable sources')
    if result.get('stages_run') != ['head']:
        errors.append('expected head-only runtime')
    if result.get('design_point', {}).get('tp') != 4:
        errors.append('expected all four TP ranks')
    verify = result.get('verify', {})
    if (verify.get('positions') != positions or verify.get('vpos') != 1
            or verify.get('enable_arp') != 1):
        errors.append('incorrect position/VPOS/ARP configuration')
    heads = oracle.get('heads', [])[:positions]
    if len(heads) != positions:
        errors.append('oracle lacks requested positions')
    else:
        want = [f"t{j}={h['argmax_token']}/{h['logit_bits']}" for j, h in enumerate(heads)]
        tokens = verify.get('per_die_tokens', {})
        if set(tokens) != {'0', '1', '2', '3'} or any(v.split() != want for v in tokens.values()):
            errors.append('per-position tokens/logit bits differ or a TP rank is missing')
    if not isinstance(result.get('total_cycles'), int) or result['total_cycles'] <= 0:
        errors.append('missing measured cycle count')
    pins = result.get('source_sha256', {})
    if not pins:
        errors.append('missing source pins')
    for name, digest in pins.items():
        path = (source_root / name).resolve()
        if not path.is_relative_to(source_root.resolve()) or not path.is_file() or sha(path) != digest:
            errors.append(f'source pin mismatch: {name}')
    return errors


def collect(stream, source_root, out):
    # Terminal rc files are published only after the runner writes its result.
    jobs = {}
    for positions in (1, 4):
        name = f'head{positions}'
        rc = int((stream / f'{name}.rc').read_text().strip())
        result_path = stream / 'res' / f'{name}.json'
        oracle_path = stream / f'head_oracle_p{positions}' / 'oracle.json'
        errors = []
        result = json.loads(result_path.read_text()) if result_path.exists() else None
        oracle = json.loads(oracle_path.read_text())
        if rc != 0:
            errors.append(f'runner exit {rc}')
        if result is None:
            errors.append('runner produced no result')
        else:
            errors += validate(result, oracle, positions, source_root)
            if result.get('oracle_sha256') != sha(oracle_path):
                errors.append('oracle pin mismatch')
        jobs[name] = {'positions': positions, 'exit_code': rc, 'errors': errors,
                      'cycles': result.get('total_cycles') if result else None,
                      'result': result, 'oracle_sha256': sha(oracle_path)}
    one, four = jobs['head1'], jobs['head4']
    if one['result'] and four['result']:
        for key in ('source_sha256', 'design_point', 'wire_stages', 'generated_core_sha256'):
            if one['result'].get(key) != four['result'].get(key):
                four['errors'].append(f'head1/head4 differ in {key}')
    passed = all(not job['errors'] for job in jobs.values())
    summary = {'schema': 'opentallas.qwen-rom-dspark-head-measured.v1',
               'status': 'PASS' if passed else 'FAIL',
               'collector_sha256': sha(__file__),
               'jobs': {name: {k: v for k, v in job.items() if k != 'result'} for name, job in jobs.items()},
               'increment_per_extra_position': (four['cycles'] - one['cycles']) / 3 if passed else None,
               'claim_boundary': 'Head-only TP4 companion RTL with preloaded final X; no drafter, rollback, overlap, near-HBM or SS/FF qualification.'}
    out.mkdir(parents=True, exist_ok=False)
    for name in jobs:
        files = [stream / f'{name}.rc', stream / 'res' / f'{name}.json',
                 stream / f'{name}.out', stream / name / 'token.log',
                 stream / name.replace('head', 'head_oracle_p') / 'oracle.json']
        dst = out / name
        dst.mkdir()
        for path in files:
            if path.exists():
                shutil.copyfile(path, dst / path.name)
    (out / 'measured_head.json').write_text(json.dumps(summary, indent=2) + '\n')
    return summary


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--stream', type=Path, required=True)
    ap.add_argument('--source-root', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--wait', action='store_true')
    args = ap.parse_args()
    while not all((args.stream / f'head{p}.rc').exists() for p in (1, 4)):
        if not args.wait:
            raise SystemExit('head jobs are not terminal')
        time.sleep(30)
    summary = collect(args.stream, args.source_root, args.out)
    print(json.dumps(summary, indent=2))
    raise SystemExit(0 if summary['status'] == 'PASS' else 1)


if __name__ == '__main__':
    main()
