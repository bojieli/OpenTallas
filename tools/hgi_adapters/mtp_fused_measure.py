#!/usr/bin/env python3
"""Fail-closed receipt for the real P-row HC_PRE_NORM unit comparison.

Input directories contain the complete run.log and generated vec/ files. This
reports component latency only; it does not qualify a die or an MTP token rate.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_run(directory, mutant=False):
    vec = directory / 'vec'
    cases = []
    for line in (vec / 'fu_case.mem').read_text().splitlines():
        assert len(line) == 72, 'incomplete case image'
        cases.append([int(line[i:i + 8], 16) for i in range(0, 72, 8)])
    data = {i: c for i, c in enumerate(cases) if c[0] == 0}
    assert data, 'missing data cases'
    text = (directory / 'run.log').read_text()
    assert not re.search(r'file not found|Unable to open|cannot open|%Error|FATAL', text, re.I), 'invalid run input'
    matches = re.findall(r'^case (\d+): (\d+) records in (\d+) cycles \(HC engine (\d+), mover (\d+)\)$', text, re.M)
    observed = {int(i): dict(records=int(n), cycles=int(c), engine_cycles=int(h), mover_cycles=int(m))
                for i, n, c, h, m in matches}
    assert len(observed) == len(matches) == len(data), 'incomplete/duplicate cycle records'
    assert set(observed) == set(data), 'unexpected measured case'
    for i, c in data.items():
        assert observed[i]['records'] == c[2], 'record did not retire'
        assert observed[i]['cycles'] > 0, 'missing measured cycles'
    summary = re.findall(r'^summary: (\d+) FUSED data cases through the D1 unit, (\d+) VM words exact$', text, re.M)
    assert len(summary) == 1 and tuple(map(int, summary[0])) == (len(data), sum(c[6] for c in data.values())), 'incomplete word check'
    target = max(data, key=lambda i: data[i][6])
    if mutant:
        failures = re.findall(r'^HGI_FUSED_UNIT FAIL errors=(\d+)$', text, re.M)
        assert len(failures) == 1 and int(failures[0]) > 0, 'mutant was not rejected'
        assert not re.search(r'^HGI_FUSED_UNIT PASS$', text, re.M), 'contradictory mutant verdict'
        assert re.search(rf'^ERR case {target} VM\[', text, re.M), 'mutant lacks a target-row numerical mismatch'
    else:
        assert len(re.findall(r'^HGI_FUSED_UNIT PASS$', text, re.M)) == 1, 'positive did not pass'
        assert not re.search(r'^ERR |^HGI_FUSED_UNIT FAIL', text, re.M), 'positive contained errors'
    return dict(target_case=target, cases=data, measured=observed,
                log_sha256=sha(directory / 'run.log'),
                image_sha256={f: sha(vec / f) for f in ('fu_vmi.mem', 'fu_vme.mem', 'fu_hbm.mem', 'fu_rec.mem', 'fu_case.mem')})


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    for name in ('baseline', 'candidate', 'mutant'):
        ap.add_argument('--' + name, required=True, type=Path)
    ap.add_argument('--rows', type=int, default=6)
    ap.add_argument('--out', required=True, type=Path)
    a = ap.parse_args()
    base, cand, mut = [read_run(getattr(a, name), name == 'mutant') for name in ('baseline', 'candidate', 'mutant')]
    for x in (cand, mut):
        for f in ('fu_vmi.mem', 'fu_vme.mem', 'fu_hbm.mem'):
            assert base['image_sha256'][f] == x['image_sha256'][f], 'comparison stimuli/answers differ'
    assert cand['image_sha256'] == mut['image_sha256'], 'mutant input programme differs'
    b = base['measured'][base['target_case']]
    c = cand['measured'][cand['target_case']]
    assert b['records'] == a.rows and c['records'] == 1, 'not serial P versus one P-row record'
    assert cand['cases'][cand['target_case']][6] == a.rows * 5120, 'not full D5120 rows'
    root = Path(__file__).resolve().parents[2]
    sources = ('rtl/hbm_accel/generic/peers/ot_hgi_hc_eng_ll.sv',
               'rtl/hbm_accel/generic/adapters/ot_hgi_fused_record.sv',
               'rtl/hbm_accel/generic/adapters/tb/tb_hgi_fused_unit.sv',
               'tools/hgi_adapters/fused_bench.py')
    receipt = dict(scope='component_only_actual_RTL_and_mapped_VM; no_die_or_token_rate_qualification', rows=a.rows,
                   source_commit=subprocess.check_output(['git', '-C', str(root), 'rev-parse', 'HEAD'], text=True).strip(),
                   source_sha256={p: sha(root / p) for p in sources}, baseline=base, candidate=cand, mutant=mut,
                   serial_cycles=b['cycles'], row_cycles=c['cycles'],
                   row_average_cycles=c['cycles'] / a.rows,
                   measured_latency_ratio=c['cycles'] / b['cycles'],
                   saved_cycles=b['cycles'] - c['cycles'],
                   note='Average row latency is not steady-state II. End-to-end measured schedule remains required.')
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps({k: receipt[k] for k in ('serial_cycles', 'row_cycles', 'measured_latency_ratio', 'saved_cycles')}))


if __name__ == '__main__':
    main()
