#!/usr/bin/env python3
"""Validate actual layer banks and produce an execution plan; never import VM."""
import argparse
import hashlib
import json
from pathlib import Path

FUSED_SHA = 'cc5bc8fc17d4068ac9a49e8bf79f34e74350d56d114dd7fe5cde433d2ac82796'

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def prepare(spec, output):
    request = json.loads(spec.read_text())
    stages = request['layers']
    if not 1 <= len(stages) <= 36:
        raise ValueError('execution plan requires one through 36 actual layers')
    pins, lines = {}, []
    previous = None
    position = request['position']
    epoch = request.get('epoch', 17)
    if not 0 <= epoch <= 65535:
        raise ValueError('token epoch exceeds actual 16-bit identity')
    if not 0 <= position < 8192:
        raise ValueError('token position exceeds actual cache')
    for stage in stages:
        layer = stage['layer']
        if not 0 <= layer < 36 or (previous is not None and layer != previous + 1):
            raise ValueError('actual layers must be contiguous and bounded')
        image, program, oracle = (Path(stage[k]).resolve() for k in ('image', 'program', 'oracle'))
        for path in (image, program, oracle):
            if any(c.isspace() for c in str(path)):
                raise ValueError('execution plan paths cannot contain whitespace')
        report = json.loads((oracle / 'oracle.json').read_text())
        if report['payload_layer'] != layer or report['position'] != position or not report['production_tp8_collective_compatible']:
            raise ValueError('layer reference identity/profile differs')
        pins[str(oracle / 'oracle.json')] = sha(oracle / 'oracle.json')
        for rank in range(8):
            meta_path = image / f'die{rank}' / f'layer{layer}_rom.json'
            meta = json.loads(meta_path.read_text())
            if meta['layer'] != layer or meta['die'] != rank or meta['tp'] != 8:
                raise ValueError('actual image layer/rank/TP identity differs')
            if meta['image_sha256'] != report['ranks'][str(rank)]['image_sha256']:
                raise ValueError('actual image differs from independent arithmetic reference')
            for name, digest in meta['image_sha256'].items():
                path = image / f'die{rank}' / name
                observed = sha(path)
                if observed != digest:
                    raise ValueError(f'actual payload byte drift: {path}')
                pins[str(path)] = observed
            path = program / f'die{rank}' / 'program.hex'
            digest = sha(path)
            if digest != FUSED_SHA or digest != report['ranks'][str(rank)]['lowered_program_sha256']:
                raise ValueError('actual native 25-word program bytes differ')
            pins[str(path)] = digest
            for kind in ('K', 'V'):
                path = oracle / f'die{rank}' / f'prior_{kind}_fp8.bin'
                if path.stat().st_size != position * 128 or sha(path) != report['ranks'][str(rank)][f'prior_{kind}_sha256']:
                    raise ValueError('declared prior cache byte/length drift')
                pins[str(path)] = sha(path)
        lines.append(f'{layer} {epoch} {position} {image} {program} {oracle}')
        previous = layer
    initial = Path(request['actual_initial_vm']).resolve()
    if not initial.is_file() or sha(initial) != request['actual_initial_vm_sha256']:
        raise ValueError('actual embedding/previous execution VM export digest differs')
    pins[str(initial)] = sha(initial)
    upstream = Path(request['actual_initial_receipt']).resolve()
    receipt = json.loads(upstream.read_text())
    if not receipt.get('passed') or receipt['actual_exports_sha256'].get(initial.name) != pins[str(initial)]:
        raise ValueError('initial VM is not a passing actual RTL export bound by its upstream receipt')
    pins[str(upstream)] = sha(upstream)
    output.mkdir(parents=True, exist_ok=False)
    (output / 'layers.plan').write_text('\n'.join(lines) + '\n')
    (output / 'input_pins.json').write_text(json.dumps({'scope': 'VALIDATED_ACTUAL_INPUTS_NOT_RTL_EXECUTION',
        'actual_initial_vm': str(initial), 'spec_sha256': sha(spec), 'payload_sha256': pins,
        'no_reference_VM_import_after_initial_actual_input': True}, indent=2) + '\n')

if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--spec', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    prepare(a.spec, a.out)
