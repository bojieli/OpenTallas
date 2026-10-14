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
    epoch = request.get('epoch', 0)
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
            lowering_path = program / f'die{rank}' / 'lowering.json'
            lowering = json.loads(lowering_path.read_text())
            descriptors = program / f'die{rank}' / 'segments.hex'
            expected_descriptors = ['0000000000000001', '0000000e00000001', '0000001600000000']
            if (lowering['candidate_program_sha256'] != digest or
                lowering['source_program_sha256'] != meta['image_sha256']['program.hex'] or
                lowering['payload_layer'] != layer or lowering['payload_die'] != rank or
                lowering['descriptor_hex'] != expected_descriptors or
                descriptors.read_text().split() != expected_descriptors):
                raise ValueError('actual source-bound AR256/window0/base0,14,22 descriptor bank differs')
            pins[str(lowering_path)] = sha(lowering_path)
            pins[str(descriptors)] = sha(descriptors)
            for kind in ('K', 'V'):
                path = oracle / f'die{rank}' / f'prior_{kind}_fp8.bin'
                if path.stat().st_size != position * 128 or sha(path) != report['ranks'][str(rank)][f'prior_{kind}_sha256']:
                    raise ValueError('declared prior cache byte/length drift')
                pins[str(path)] = sha(path)
        lines.append(f'{layer} {epoch} {position} {image} {program} {oracle}')
        previous = layer
    if 'actual_stage0' in request:
        if 'actual_initial_vm' in request or stages[0]['layer'] != 0 or position != 0:
            raise ValueError('cold actual stage0 requires layer0/position0 and no VM import')
        stage0 = request['actual_stage0']
        program = Path(stage0['program']).resolve()
        if sha(program) != stage0['program_sha256'] or len(program.read_text().split()) != 2:
            raise ValueError('actual embedding two-word program drift')
        pins[str(program)] = sha(program)
        for name, digest in stage0['bank_sha256'].items():
            path = Path(stage0['bank']).resolve() / 'token0' / name
            if name not in ('codes.hex', 'scale.hex') or sha(path) != digest:
                raise ValueError('actual checkpoint embedding operand drift')
            pins[str(path)] = sha(path)
        initial_mode = 'ZERO_COLD_VM_THEN_REAL_EMBEDDING_AFTER_ACTUAL_HOST_COHORT'
    else:
        initial = Path(request['actual_initial_vm']).resolve()
        if not initial.is_file() or sha(initial) != request['actual_initial_vm_sha256']:
            raise ValueError('actual embedding/previous execution VM export digest differs')
        pins[str(initial)] = sha(initial)
        upstream = Path(request['actual_initial_receipt']).resolve()
        receipt = json.loads(upstream.read_text())
        if not receipt.get('passed') or receipt['actual_exports_sha256'].get(initial.name) != pins[str(initial)]:
            raise ValueError('initial VM is not a passing actual RTL export bound by its upstream receipt')
        pins[str(upstream)] = sha(upstream)
        initial_mode = 'STAGED_ACTUAL_VM_EXPORT_IMPORT'
    output.mkdir(parents=True, exist_ok=False)
    (output / 'layers.plan').write_text('\n'.join(lines) + '\n')
    (output / 'input_pins.json').write_text(json.dumps({'scope': 'VALIDATED_ACTUAL_INPUTS_NOT_RTL_EXECUTION',
        'initial_mode': initial_mode, 'spec_sha256': sha(spec), 'payload_sha256': pins,
        'no_reference_VM_import_after_initial_actual_input': True}, indent=2) + '\n')

if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--spec', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    prepare(a.spec, a.out)
