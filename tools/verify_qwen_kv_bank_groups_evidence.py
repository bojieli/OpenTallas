#!/usr/bin/env python3
"""Check source, implementation, additive evidence and original capture pins."""
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'results/uarch/qwen_rom_kv_bank_groups_20261002'


def verify():
    def obj(name):
        return json.loads((OUT / name).read_text())

    def check(path, digest):
        if hashlib.sha256((ROOT / path).read_bytes()).hexdigest() != digest:
            raise ValueError('pin mismatch: ' + path)

    artifacts = obj('artifact-sha256-r1.json')
    for path, digest in artifacts.items():
        check(path, digest)
    implementations = obj('implementation-pins-r1.json')
    for path, digest in implementations.items():
        check(path, digest)
    model = obj('model-r4.json')
    for path, digest in model['implementation_sha256'].items():
        check(path, digest)
    for path, digest in model['source_sha256'].items():
        check(path, digest)
        raw = subprocess.check_output(['git', 'show', model['parent'] + ':' + path], cwd=ROOT)
        if hashlib.sha256(raw).hexdigest() != digest:
            raise ValueError('source parent mismatch: ' + path)
    original = obj('preservation-r1.json')
    for path, digest in original['pinned_original_sha256'].items():
        check(path, digest)
    capture = original['numerical_capture']
    check(capture['capture_path'], capture['capture_sha256'])
    for row in model['calendar']['rows']:
        f = row['finite_conditional_reservation']
        if (f['command_count_per_stack'] != [32736] * 4
                or f['owned_data_and_grant_count_per_stack'] != [65472] * 4
                or not f['all_reverse_grants_reserved']):
            raise ValueError('finite reservation source debit mismatch')
    if model['calendar']['adopted_rate'] is not None or model['admission']['hardware_admitted']:
        raise ValueError('unqualified adoption')
    return dict(verdict='PASS_PINS_AND_CONDITIONAL_RESERVATION_ONLY',
                source_pins=len(model['source_sha256']), artifacts=len(artifacts),
                implementation_pins=len(implementations),
                immutable_originals=len(original['pinned_original_sha256']),
                layers=len(model['calendar']['rows']), hardware_admitted=False,
                actual_production_qualified=False)


if __name__ == '__main__':
    print(json.dumps(verify(), sort_keys=True))
