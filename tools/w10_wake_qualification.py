#!/usr/bin/env python3
"""Admit only a modeled, source-pinned, same-cycle full golden wake correction."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def validate_model(model):
    if model['verdict'] != 'PASS_SIZING_ONLY' or model['parameters'] != dict(
            WAKE_REG=1, default=0, FAST=1, PP=1, FRONT_PAR=0, NB=2, LAT=8):
        raise ValueError('unqualified model or parameters')
    if model['latency']['added_walker_cycles'] != 0:
        raise ValueError('golden latency must remain unchanged')
    if model['full_size']['maximum_pairs_per_die'] < 4773 or model['full_size']['layer_dies'] != 164:
        raise ValueError('undersized field')
    for key, shape in [('q', [510.84, 126.9]), ('column', [1002.89, 142.56])]:
        r = model['elements'][key]
        if r['outline_um'] != shape or not r['fit'] or r['local_signal_tracks_needed'] >= r['channel_tracks_estimate']:
            raise ValueError('full-goal slot or tracks do not fit')


def compare_cases(baseline, candidate):
    if baseline['verdict'] != 'PASS' or candidate['verdict'] != 'PASS':
        raise ValueError('failed golden verdict')
    if baseline['params'] != candidate['params'] or baseline['params']['LAT'] != 8:
        raise ValueError('parameter drift')
    for key in ['checkpoint_revision','checkpoint_header_sha256','seed','golden']:
        if baseline[key] != candidate[key]:
            raise ValueError('checkpoint or golden drift')
    if len(baseline['cases']) != 13 or baseline['cases'] != candidate['cases']:
        raise ValueError('full cases or golden latency differ')
    for c in candidate['cases']:
        if c['N'] != 4 or c['NB'] != 2 or c['rows'] != c['fp32_exact'] or c['rows'] != c['bf16_exact'] or c['fault']:
            raise ValueError('not the qualified full legal shape')
    return sum(c['rows'] for c in candidate['cases'])


def verify_sources(rec):
    if not rec['source_sha256']:
        raise ValueError('missing source pins')
    for path, expected in rec['source_sha256'].items():
        actual = hashlib.sha256((ROOT/path).read_bytes()).hexdigest()
        if actual != expected:
            raise ValueError('source drift: '+path)


def qualify(model, control, baseline, candidate):
    validate_model(model)
    for rec in [model, control, baseline, candidate]:
        verify_sources(rec)
    if control['verdict'] != 'PASS' or len(control['runs']) != 2 or not all(r['passed'] for r in control['runs']):
        raise ValueError('wake/reset/drain or mutant gate failed')
    if control['runs'][0]['added_cycles'] != 0 or control['runs'][0]['coverage']['rows'] < 84:
        raise ValueError('control latency or coverage insufficient')
    rows = compare_cases(baseline, candidate)
    wrapper_paths = [p for p in candidate['source_sha256'] if p.endswith('array_wake_binding.sv')]
    if len(wrapper_paths) != 1:
        raise ValueError('missing isolated wake binding')
    original = (ROOT/'rtl/test/w10_validation/ot_v41_rom_array_w10_test.sv').read_text()
    expected = original.replace('ot_v41_rom_elem_w10 #(', 'ot_v41_rom_elem_wake_w10 #(').replace(
        '.FRONT_PAR(FRONT_PAR),', '.FRONT_PAR(FRONT_PAR), .WAKE_REG(1),')
    if Path(wrapper_paths[0]).read_text() != expected:
        raise ValueError('golden binding changes more than wake selection')
    return dict(verdict='PASS_EXACT_PREPHYSICAL', adopted=False, rows=rows,
                cases=13, completion_cycle_delta=0, full_case_records_identical=True,
                unchanged_baseline_source_pins=True,
                full_shape=dict(N=4,NB=2,MTP=6,FAST=1,PP=1,FRONT_PAR=0,LAT=8),
                pending=['actual full-goal floorplan and synthesis leaf-clone check',
                         'SS/FF contextual timing, clean route and real abstract',
                         'clock power, hub layers, die root/region and actual IR'])


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    for key in ['model','control','baseline','candidate','output']:
        ap.add_argument('--'+key,type=Path,required=True)
    a = ap.parse_args()
    rec = qualify(*(json.loads(getattr(a,k).read_text()) for k in ['model','control','baseline','candidate']))
    rec['input_sha256'] = {k:hashlib.sha256(getattr(a,k).read_bytes()).hexdigest() for k in ['model','control','baseline','candidate']}
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with a.output.open('x') as f:
        json.dump(rec,f,indent=2);f.write('\n')
    print(json.dumps(rec,indent=2))
