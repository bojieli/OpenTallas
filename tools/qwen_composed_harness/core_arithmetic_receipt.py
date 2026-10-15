#!/usr/bin/env python3
"""Validate completed source-pinned RTL FP core; never imply native chip coverage."""
import argparse
import hashlib
import json
from pathlib import Path


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def validate(core):
    receipt_path = core.parent / 'receipt.json'
    r = json.loads(receipt_path.read_text())
    command = r['command']
    if r['exit'] != 0 or not r.get('hierarchical'):
        raise ValueError('RTL FP hierarchical build must have completed successfully')
    if '-GG=3072' not in command or '-GLV=6' not in command:
        raise ValueError('requires actual production G3072 LV6 core')
    if r.get('fp_units') != 'RTL rtl/hdc/ot_hdc_fastfp.sv':
        raise ValueError('C/DPI arithmetic cannot establish RTL FP coverage')
    pins = r['source_sha256']
    if not any(Path(p).name == 'ot_hdc_fastfp.sv' for p in pins):
        raise ValueError('real FP arithmetic source missing')
    for path, expected in pins.items():
        p = Path(path)
        if digest(p) != expected:
            raise ValueError(f'frozen arithmetic source changed: {p}')
        if p.suffix in ('.sv', '.svh') and 'DPI-C' in p.read_text():
            raise ValueError(f'DPI import in core RTL: {p}')
    archives = sorted(core.rglob('*.a'))
    parent = core / 'Vot_hdc_core_vector_weight_native_candidate__ALL.a'
    if parent not in archives:
        raise ValueError('actual compiled parent archive missing')
    if len(archives) < 2:
        raise ValueError('compiled hierarchical FP children missing')
    return {
        'scope': 'core RTL arithmetic only; memory, links, full token not qualified',
        'native_full_token': False,
        'core_arithmetic': 'source-pinned RTL FP hierarchical G3072 LV6',
        'receipt_sha256': digest(receipt_path),
        'source_sha256': pins,
        'archives_sha256': {str(p): digest(p) for p in archives},
        'eval_memo': 'disabled: child arithmetic pipelines contain sequential state',
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--core', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    evidence = validate(a.core)
    a.output.write_text(json.dumps(evidence, indent=2) + '\n')


if __name__ == '__main__':
    main()
