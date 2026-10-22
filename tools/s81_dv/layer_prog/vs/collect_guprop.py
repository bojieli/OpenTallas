#!/usr/bin/env python3
"""Collect the 98/84 GU consumer campaign; transport and capacity stay separate.

Usage: collect_guprop.py RESULTS --source-ref REF [--out RECEIPT]
The historical runner exits zero even for failed vectors. Require complete named
positives and causal negatives instead of interpreting its process status.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess


def collect(directory, source_ref):
    d = Path(directory)
    root = Path(__file__).resolve().parents[4]
    matched = 0
    for line in (d / 'sources.sha256').read_text().splitlines():
        digest, name = line.split(None, 1)
        source = subprocess.check_output(['git', '-C', str(root), 'show', f'{source_ref}:{name.strip()}'])
        assert hashlib.sha256(source).hexdigest() == digest, ('source mismatch', name)
        matched += 1
    assert matched > 0, 'empty source manifest'
    texts = [(d / f'run_m{i}.txt').read_text() for i in (0, 1)]
    verdicts = {}
    for text in texts:
        for name, verdict in re.findall(r'^GPB (\S+) (PASS|FAIL|NOVERDICT)$', text, re.M):
            assert name not in verdicts, ('duplicate vector', name)
            verdicts[name] = verdict
    positives = [f'm0_f{f}_G{g}' for f in (98, 84) for g in range(63)]
    assert all(verdicts.get(n) == 'PASS' for n in positives), 'missing/failed production leaf'
    selected = (4, 13, 22, 31, 58)
    negatives = [f'm0_{mu}_f98_G{g}' for mu in ('srcoff', 'gswap') for g in selected]
    negatives += [f'm1_f98_G{g}' for g in selected if g != 58]
    assert all(verdicts.get(n) == 'FAIL' for n in negatives), 'missing/ineffective negative'
    for name in negatives:
        text = texts[int(name[1])]
        block = re.search(r'^GPB ' + re.escape(name) + r' FAIL\n(.*?)(?=^GPB |\Z)', text, re.M | re.S)
        assert block and 'MISMATCH' in block[1], ('no causal mismatch witness', name)
    # Drop-router-weight mutation does not affect the unweighted shared expert.
    assert verdicts.get('m1_f98_G58') == 'PASS', 'shared control unexpectedly affected'
    maps = {}
    for f in (98, 84):
        m = json.loads((d / f'g{f}gp.json').read_text())
        assert m['PASS'] and m['cap_faults'] == m['gu_slot_collisions'] == m['refused'] == 0
        assert len(m['records']) == 1008
        maps[f] = dict(frames=sum(m['topo']), topology=m['topo'], slice_share=m['slice_share'], records=1008)
        assert maps[f]['frames'] == f
    return dict(verdict='PASS', scope='capture-map layout and injected-RD SW consumer arithmetic only',
                source_ref=source_ref, source_files_matched=matched, positive_leaves=126,
                causal_negatives=14, shared_mutant_control='PASS (weight-independent)', maps=maps,
                transport_qualified=False, stage_capacity_qualified=False, mu_calendar_qualified=False,
                artifacts={p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(d.iterdir())
                           if p.is_file() and p.suffix != '.receipt'})


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('results')
    ap.add_argument('--source-ref', required=True)
    ap.add_argument('--out')
    a = ap.parse_args()
    result = collect(a.results, a.source_ref)
    content = json.dumps(result, indent=2) + '\n'
    if a.out:
        Path(a.out).write_text(content)
    print(content, end='')
