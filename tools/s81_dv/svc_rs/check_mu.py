#!/usr/bin/env python3
"""Fail-closed component gate; off-chip HBM is stimulus, SRAM remains DUT RTL/macros."""
import argparse
from pathlib import Path


def traces(text, job, shift=0):
    out = []
    for line in text.splitlines():
        words = line.split()
        if len(words) >= 5 and words[:2] == ['SVCRS_TR', str(job)]:
            # Requests contain transaction tags; numerical/visibility outputs are compared here.
            if words[3] != 'RQ':
                out.append((int(words[2]) - shift, *words[3:]))
    if not out:
        raise ValueError(f'missing trace for job {job}')
    return out


def check(directory, start2):
    logs = {name: (directory / f'{name}.log').read_text() for name in
            ('single_u0', 'mu', 'mut_sb', 'mut_user', 'single_u1', 'default')}
    config = f'SVCRS_CONFIG sram_macro=1 static_io=1 start2={start2}'
    for name, log in logs.items():
        if config not in log.splitlines():
            raise ValueError(f'{name}: missing mapped SRAM/static launch configuration')
    for name in ('single_u0', 'single_u1', 'default'):
        verdicts = [s for s in logs[name].splitlines() if s.startswith('SVCRS ')]
        if len(verdicts) != 1 or not verdicts[0].endswith('verdict=PASS'):
            raise ValueError(f'{name}: missing or failing component verdict')
    for name in ('mu', 'mut_sb', 'mut_user'):
        jobs = [s for s in logs[name].splitlines() if s.startswith('SVCRS_JOB ')]
        aggregate = [s for s in logs[name].splitlines() if s.startswith('SVCRS_MU ')]
        expected = 'PASS' if name == 'mu' else 'FAIL'
        if len(jobs) != 2 or len(aggregate) != 1:
            raise ValueError(f'{name}: missing or duplicate job/aggregate verdict')
        if 'job=0 ' not in jobs[0] or not jobs[0].endswith('verdict=PASS'):
            raise ValueError(f'{name}: mutant must preserve latency user')
        if 'job=1 ' not in jobs[1] or not jobs[1].endswith(f'verdict={expected}'):
            raise ValueError(f'{name}: job 1 expected {expected}')
        if not aggregate[0].endswith(f'verdict={expected}'):
            raise ValueError(f'{name}: aggregate expected {expected}')
    if traces(logs['single_u0'], 0) != traces(logs['mu'], 0):
        raise ValueError('latency user output cycle/data trace changed')
    if traces(logs['single_u1'], 0) != traces(logs['mu'], 1, start2):
        raise ValueError('user 1 output trace is not exact fixed shift')
    print(f'SVCRS_MU_GATE PASS component_only=1 user1_shift={start2}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    parser.add_argument('--start2', type=int, default=8192)
    args = parser.parse_args()
    try:
        check(args.directory, args.start2)
    except (OSError, ValueError) as error:
        parser.exit(1, f'SVCRS_MU_GATE FAIL: {error}\n')
