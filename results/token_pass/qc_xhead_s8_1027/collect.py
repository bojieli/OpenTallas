#!/usr/bin/env python3
"""Collect actual bound-row xhead cases; absent cases never pass."""
import argparse
import json
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument('run_dir', type=Path)
a = p.parse_args()
rows, errors = [], []
for consumer in ('qkv', 'gu', 'o', 'down'):
    mutants = (None, 'goearly') if consumer == 'qkv' else (None, 'goearly', 'xpflate', 'isaxbase')
    for mutant in mutants:
        tag = f'{consumer}_{mutant or "m0"}'
        path = a.run_dir / 'runs' / f'xhead_{tag}.json'
        result = json.loads(path.read_text()) if path.is_file() else {}
        expected = 'FAIL' if mutant else 'PASS'
        actual = result.get('verdict', 'NOT RUN')
        if actual != expected:
            errors.append(f'{tag}: expected {expected}, got {actual}')
        rows.append(dict(case=tag, expected=expected, verdict=actual, result=result))
result = dict(stage='xhead_s8', verdict='FAIL' if errors else 'PASS',
              source_base='a54fa8a6c', vehicle='tb_qfd_dv2 FACE3 bound s8 row, CROM3/MIF0',
              scope='Component functional gate; not a whole-die or whole-token pass',
              problems=errors, cases=rows,
              consumer_ages=json.loads((a.run_dir / 'xhead_ages.json').read_text())
              if (a.run_dir / 'xhead_ages.json').is_file() else None)
(a.run_dir / 'result.json').write_text(json.dumps(result, indent=1) + '\n')
print('XHEAD_S8', result['verdict'], len(rows), 'cases', errors)
raise SystemExit(bool(errors))
