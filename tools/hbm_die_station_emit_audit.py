#!/usr/bin/env python3
"""Audit every actual station's positive/mutant emission without suppressing failures.

Consumes completed production ports.json files and the exact fc_map receipt;
never builds a replacement model, invents pin directions, or qualifies timing.
"""
import argparse
import ast
import importlib.util
import json
from pathlib import Path
import traceback


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--ports', type=Path, required=True)
    ap.add_argument('--forwarded-map', type=Path, required=True)
    ap.add_argument('--generator', type=Path, default=Path(__file__).with_name('hbm_die_station_gen.py'))
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    spec = importlib.util.spec_from_file_location('actual_station_generator', a.generator)
    g = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(g)
    fc = {ast.literal_eval(k): v for k, v in json.loads(a.forwarded_map.read_text()).items()}
    report = {'status': 'diagnostic, no RTL binding or timing qualification',
              'ports': str(a.ports), 'forwarded_map': str(a.forwarded_map), 'pass': [], 'fail': []}
    for p in sorted(a.ports.glob('*/ports.json')):
        name = p.parent.name
        if name.split('_')[1] not in ('stn', 'meso', 'mcast', 'gath', 'cdist'):
            continue
        try:
            rec = json.loads(p.read_text())
            g.build(rec, fc)
            g.build(rec, fc, mutant=True)
            report['pass'].append(name)
        except Exception as e:
            report['fail'].append({'master': name, 'error': repr(e), 'traceback': traceback.format_exc()})
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(report, indent=1) + '\n')
    print(json.dumps({'pass': len(report['pass']), 'fail': len(report['fail'])}))
    return bool(report['fail'])


if __name__ == '__main__':
    raise SystemExit(main())
