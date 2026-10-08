#!/usr/bin/env python3
"""Reuse the actual full-shape WINDOW golden/DRAM gate for the default-off pipeline.

No native S81 wiring or golden-format changes. The original gate and vectors
are reused; only the source parameter and successor modules are added.
"""
import argparse
import json
import hashlib
from pathlib import Path
import dsrom_s81_window_la as gate

PIPELINE = [f'rtl/dsrom_sys/s81_window_la/pipeline/ot_dsrom_window_{name}_pipeline.sv'
            for name in ('writer', 'stage', 'source', 'row_merge')]
CTL_MANIFEST = Path('rtl/dsrom_sys/s81_window_la/recovered_ctl_m2/source_manifest.json')


def controller_sources(mutant=False):
    """Select the isolated, byte-identical controller campaign sources."""
    manifest = json.loads((gate.ROOT / CTL_MANIFEST).read_text())
    sources = []
    for entry in manifest['sources']:
        path = gate.ROOT / entry['recovered']
        if hashlib.sha256(path.read_bytes()).hexdigest() != entry['sha256']:
            raise ValueError('recovered controller source hash mismatch: ' + str(path))
        if mutant or path.name != 'mutant_window_ctl_late_payload.sv':
            sources.append(entry['recovered'])
    # This file defines a preprocessor switch consumed by the controller.
    # Preserve the original campaign's definition-before-controller ordering.
    if mutant:
        sources.sort(key=lambda s: Path(s).name != 'mutant_window_ctl_late_payload.sv')
    return sources


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--vectors', type=Path, required=True)
    p.add_argument('--verilator', required=True)
    p.add_argument('--only', default='lf,lf_cold,lf_scan,lf_bg,lf_kg_p1,lf_kg_p2,lf_kgcon_p2')
    p.add_argument('--jobs', type=int, default=1)
    p.add_argument('--stage-margin', type=int, default=0, choices=(0, 1),
                   help='ot_dsrom_window_stage_pipeline MARGIN (default off)')
    p.add_argument('--ctl-leaf', type=int, default=0, choices=(0, 1, 2, 3),
                   help='isolated pinned controller leaf with MARGIN 0/1/2')
    p.add_argument('--mutant-late-payload', action='store_true',
                   help='controller negative: capture K-port request payload one edge late')
    a = p.parse_args()
    if a.ctl_leaf and a.stage_margin:
        p.error('controller recovery and newer stage-margin are separate source vehicles')
    if a.mutant_late_payload and not a.ctl_leaf:
        p.error('--mutant-late-payload requires --ctl-leaf')
    a.plan = json.dumps({0:['lf','lf_cold'], 20:['lf_scan','lf_bg'],
                        24:['lf','lf_kg_p1','lf_kg_p2','lf_kgcon_p2']})
    if a.ctl_leaf:
        gate.SOURCES[:] = controller_sources(a.mutant_late_payload)
    else:
        gate.SOURCES.extend(PIPELINE)
    for name in a.only.split(','):
        gate.CONFIGS[name]['WINDOW_PIPELINE'] = 1
        if a.stage_margin:
            gate.CONFIGS[name]['STAGE_MARGIN'] = 1
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
