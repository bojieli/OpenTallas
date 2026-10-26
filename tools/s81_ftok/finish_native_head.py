#!/usr/bin/env python3
"""Join complete actual-HC -> ROM-head roots to the real TP4 terminal.

The expected token/bits are a separately supplied checker input. They are never
used to construct field roots or logits. VM delivery and whole-token native
qualification remain outside this component-chain gate.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

from collect_native_head_field import collect


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--ranks', nargs=4, required=True, type=Path)
    p.add_argument('--output', required=True, type=Path)
    p.add_argument('--expect', required=True, type=Path)
    a = p.parse_args()
    expected = a.expect.read_text().split()
    if len(expected) != 2 or any(len(x) != 8 for x in expected):
        raise ValueError('independent expectation must contain token and logit bits')
    for rank, directory in enumerate(a.ranks):
        rec = json.loads((directory/'record.json').read_text())
        xf = rec.get('xf_provenance', {})
        if (not rec.get('native_xf_chained') or xf.get('gate') != 'PASS'
                or xf.get('arithmetic') != 'RTL only; no DPI'
                or not xf.get('rtl_sources') or not xf.get('actual_output_sha256')):
            raise ValueError(f'rank {rank} lacks actual RTL HC output provenance')
    field = collect(a.ranks, a.output)
    if not field['native_xf_chained'] or field['rows'] != 129280:
        raise ValueError('actual full-row HC-to-field chain required')
    shutil.copyfile(a.expect, a.output/'expect.mem')
    # The terminal bench compares every logit against an independent checker.
    # Never use rtl_logits_r*.mem as these expected values.
    checker_logits = {}
    for rank in range(4):
        src = a.expect.parent/f'logits_r{rank}.mem'
        words = src.read_text().split()
        if len(words) != 32320 or any(len(x) != 8 for x in words):
            raise ValueError(f'independent checker logits missing rank {rank}')
        shutil.copyfile(src, a.output/src.name)
        checker_logits[src.name] = dict(path=str(src), sha256=sha(src))
    terminal = Path(__file__).with_name('head_stage.py')
    verdicts = []
    for mutant in (0, 1):
        r = subprocess.run([sys.executable, str(terminal), 'run', '--work', str(a.output),
                            '--mut', str(mutant)], capture_output=True, text=True)
        (a.output/f'terminal_m{mutant}.log').write_text(r.stdout+r.stderr)
        want = 'S81_HEAD PASS' if mutant == 0 else 'S81_HEAD FAIL'
        if r.returncode or want not in r.stdout:
            raise RuntimeError(f'terminal m{mutant} failed gate: {r.stdout[-1000:]} {r.stderr[-1000:]}')
        verdicts.append(dict(mutant=mutant, expected='FAIL' if mutant else 'PASS', stdout=r.stdout))
    receipt = dict(schema='opentallas.s81.actual_hc_head_terminal.v1', gate='PASS',
                   actual_hc_xf_chained=True, all_field_roots_from_rtl=True, rows=129280,
                   full_native_token_qualified=False,
                   scope='actual HC arithmetic -> mapped ROM head -> TP4 terminal; VM/input producers and physical composition unqualified',
                   expected_checker=dict(path=str(a.expect), sha256=sha(a.expect),
                                         token=int(expected[0],16), bits=expected[1]),
                   field_provenance_sha256=sha(a.output/'field.provenance.json'),
                   independent_checker_logits=checker_logits,
                   tools={x.name:sha(x) for x in (Path(__file__), terminal,
                          Path(__file__).with_name('collect_native_head_field.py'))},
                   terminal=verdicts)
    (a.output/'native_chain.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(receipt,indent=2))


if __name__ == '__main__':
    main()
