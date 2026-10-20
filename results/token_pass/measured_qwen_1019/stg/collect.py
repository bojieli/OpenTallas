#!/usr/bin/env python3
"""TOKSIM-QW/STG 10-19: fold the run.sh outputs (pulled to <here>/<cfg>/) into record.json.
usage: collect.py   (reads base/ and rel/ next to this file; writes record.json)"""
import json
import re
import sys
from pathlib import Path

H = Path(__file__).resolve().parent
XT1 = H / 'xt1_dh2_summary.json'


def parse(out):
    lines = out.read_text().splitlines()
    first = lines[0] if lines else ''
    rc = next((int(l[3:]) for l in lines[::-1] if l.startswith('rc=')), None)
    m = re.match(r'DV_LOWER_(VEC|MAT) (\S+) (PASS|FAIL|REFUSED)\s*(\d+/\d+)?', first)
    r = dict(verdict=m.group(3) if m else 'ERROR', checks=m.group(4) if m else None, rc=rc, first_line=first[:400])
    js = first[first.find('{'):] if '{' in first else ''
    info = {}
    if js:
        try:
            info = json.loads(js)
        except ValueError:
            info = {}
    sp = re.search(r'span_cycles[=:"\s]+(\d+)', first)
    r['span_cycles'] = info.get('span_cycles', int(sp.group(1)) if sp else None)
    r['delivery_span_cycles'] = info.get('delivery_span_cycles')
    ig = re.search(r'isa_gold_words=(\d+/\d+)', first)
    r['isa_gold_words'] = ig.group(1) if ig else (info.get('isa_gold') or None)
    if r['verdict'] != 'PASS':
        r['detail'] = [l.strip() for l in lines[1:6]]
    return r


def main():
    rec = dict(schema='opentallas.toksim-qw.stg.v1', lane='TOKSIM-QW/STG', date='2026-10-19', position=8191, layers=[0, 1],
               cfgs={})
    for cfg in ('base', 'rel'):
        d = H / cfg
        if not d.exists():
            continue
        c = dict(stages={})
        for f in ('verilator.txt', 'timing.txt'):
            if (d / f).exists():
                c[f.split('.')[0]] = (d / f).read_text().strip()
        for cal in ('slice_calibrate.out', 'calibrate.out', 'cal_mat_calibrate.out'):
            if (d / cal).exists():
                c[cal] = (d / cal).read_text().strip().splitlines()[-3:]
        for a in ('slice_ages.json', 'vec_ages.json', 'stn_ages.json'):
            if (d / a).exists():
                c[a] = json.loads((d / a).read_text())
        for b in sorted((d / 'runs').glob('*/bench.out')):
            c['stages'][b.parent.name] = parse(b)
        rec['cfgs'][cfg] = c
    if XT1.exists():
        rec['xt1_dh2'] = json.loads(XT1.read_text())
    (H / 'record.json').write_text(json.dumps(rec, indent=1) + '\n')
    for cfg, c in rec['cfgs'].items():
        for k, v in c['stages'].items():
            print(cfg, k, v['verdict'], v['checks'], v['span_cycles'], v['delivery_span_cycles'], v['isa_gold_words'])


if __name__ == '__main__':
    sys.exit(main())
