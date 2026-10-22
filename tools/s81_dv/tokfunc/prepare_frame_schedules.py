#!/usr/bin/env python3
"""Prepare immutable current-source LP timing models before layer compilation.

This extracts source wiring only. It does not qualify a programme, physical
view, collective capture calendar, or complete token.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / 'tools/s81_dv'), str(ROOT / 'tools/s81_dv/layer_prog')]
import dv_layer_compile as C
import frame_schedule as F
from lower_xs import base_master


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--tree', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    die = C.Die(a.tree)
    selected = sorted({die.inst[f]['master'] for s in die.slices() for f in die.frames_of(s)
                       if die.inst[f]['master'].endswith('_lp')})
    directory = ROOT / 'results/arch/s81_dv_1016/frame_l4_cluster/compiler'
    names = sorted({base_master(m) for m in selected})
    manifest = a.out / 'manifest.json'
    if a.out.exists():
        prior = json.loads(manifest.read_text())
        if prior['die_sha256'] != die.die_sha or prior['selected_masters'] != selected:
            raise ValueError('preserve existing models: selected die/master identity changed; use a fresh output')
        for name in names:
            model = a.out / (name + '_schedule.json')
            if digest(model) != prior['models'][name]['sha256']:
                raise ValueError('existing model artifact changed: ' + str(model))
            data = json.loads(model.read_text())
            for f, expected in data['source_sha256'].items():
                if digest(ROOT / f) != expected:
                    raise ValueError('existing model source changed: ' + f)
            spec = directory / (name + '_spec.json')
            if digest(spec) != prior['models'][name]['spec_sha256']:
                raise ValueError('existing extraction spec changed: ' + str(spec))
        print('reused source-qualified LP models', names)
        return
    # Generate all models before publishing the manifest; partial failure is
    # retained and requires a fresh output, never silently treated as complete.
    a.out.mkdir(parents=True)
    models = {}
    for name in names:
        spec = directory / (name + '_spec.json')
        data = F.extract(spec)
        canonical = 'rtl/dsrom_sys/s81_dv/frame_lp/' + name + '_l4_lp.sv'
        if canonical not in data['source_sha256']:
            raise ValueError('materialized selected LP source is absent: ' + canonical)
        path = a.out / (name + '_schedule.json')
        path.write_text(json.dumps(data, indent=1) + '\n')
        models[name] = dict(file=path.name, sha256=digest(path), spec_sha256=digest(spec))
    manifest.write_text(json.dumps(dict(schema='opentallas.s81.lp_source_models.v1',
        die_sha256=die.die_sha, selected_masters=selected, models=models,
        qualification='SOURCE EXTRACTION ONLY; current programme and physical binding remain separate'), indent=1) + '\n')
    print('prepared current-source LP models', names)


if __name__ == '__main__':
    main()
