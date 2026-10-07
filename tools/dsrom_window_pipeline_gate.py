#!/usr/bin/env python3
"""Reuse the actual full-shape WINDOW golden/DRAM gate for the default-off pipeline.

No native S81 wiring or golden-format changes. The original gate and vectors
are reused; only the source parameter and successor modules are added.
"""
import argparse
import json
from pathlib import Path
import dsrom_s81_window_la as gate

PIPELINE = [f'rtl/dsrom_sys/s81_window_la/pipeline/ot_dsrom_window_{name}_pipeline.sv'
            for name in ('writer', 'stage', 'source', 'row_merge')]
CTL = 'rtl/dsrom_sys/s81_window_la/pipeline/ot_dsrom_window_source_ctl.sv'
MUTANT = 'rtl/dsrom_sys/s81_window_la/pipeline/mutant_window_ctl_late_payload.sv'


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--vectors', type=Path, required=True)
    p.add_argument('--verilator', required=True)
    p.add_argument('--only', default='lf,lf_cold,lf_scan,lf_bg,lf_kg_p1,lf_kg_p2,lf_kgcon_p2')
    p.add_argument('--jobs', type=int, default=1)
    p.add_argument('--ctl-leaf', type=int, default=0, choices=(0, 1, 2),
                   help='1/2: source control leaf ot_dsrom_window_source_ctl with MARGIN 0/1')
    p.add_argument('--mutant-late-payload', action='store_true',
                   help='negative control: the K-port request slice captures its payload one edge late (must FAIL)')
    a = p.parse_args()
    a.plan = json.dumps({0:['lf','lf_cold'], 20:['lf_scan','lf_bg'],
                        24:['lf','lf_kg_p1','lf_kg_p2','lf_kgcon_p2']})
    gate.SOURCES.extend(PIPELINE)
    if a.ctl_leaf:
        gate.SOURCES.extend(['rtl/hdc/ot_hdc_prefix.sv'] + ([MUTANT] if a.mutant_late_payload else []) + [CTL])
    for name in a.only.split(','):
        gate.CONFIGS[name]['WINDOW_PIPELINE'] = 1
        if a.ctl_leaf:
            gate.CONFIGS[name]['CTL_LEAF'] = a.ctl_leaf
    gate.cmd_run(a)
    runs=json.loads((a.out/'runs.json').read_text())
    rows = runs['runs'] if isinstance(runs,dict) and 'runs' in runs else runs
    # Original gate schema retains source hashes and every failed verdict.
    if isinstance(rows,dict):
        rows=rows.get('cases',[])
    if not rows or any(r['verdict']!='PASS' for r in rows):
        raise SystemExit('pipeline exactness gate failed: retained runs.json')


if __name__=='__main__':
    main()
