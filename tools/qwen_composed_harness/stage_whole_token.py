#!/usr/bin/env python3
"""Stage the whole-token inputs: validated 36-layer plan, head banks, mutant root.

Inputs are the immutable payload banks (images/, fused_images/, head_images/,
oracle/) and the canonical plan (head programs/segments, final-norm constants).
No expected value enters a DUT input: oracles are only bound for observers.
"""
import argparse, hashlib, json, os, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def oracle_dir(banks, token, layer):
    o = banks / 'oracle'
    if token == 0:
        return o / ('cold_token0_first2' if layer < 2 else 'cold_token0_continue2_to35') / f'layer{layer}'
    return o / 'cold_token65536_all36_v2' / f'layer{layer}'


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--banks', type=Path, required=True)
    p.add_argument('--canonical', type=Path, required=True)
    p.add_argument('--stage', type=Path, required=True)
    p.add_argument('--layers', type=int, default=36)
    p.add_argument('--token', type=int, default=0)
    p.add_argument('--name', required=True)
    p.add_argument('--embedding', type=Path, default=Path('/srv/opentallas-scratch/codex/qwen-host-embedding-1014/embedding'))
    p.add_argument('--mutant', help='layer:rank:line:column -- flip the high bit of one INT8 weight nibble (sign of a gate/up/down weight) in a copy')
    a = p.parse_args()
    banks, stage = a.banks.resolve(), a.stage.resolve()
    images = banks / 'images'
    if a.mutant:
        layer, rank, line, column = map(int, a.mutant.split(':'))
        root = stage / f'mutant_images_{a.name}'
        root.mkdir(parents=True, exist_ok=False)
        for d in sorted(images.iterdir()):
            if d.name != f'layer{layer}':
                os.symlink(d, root / d.name)
                continue
            (root / d.name).mkdir()
            for die in sorted(d.iterdir()):
                if die.name != f'die{rank}':
                    os.symlink(die, root / d.name / die.name)
                    continue
                (root / d.name / die.name).mkdir()
                for f in die.iterdir():
                    if f.name != 'matrix_int8.hex':
                        os.symlink(f, root / d.name / die.name / f.name)
                text = (die / 'matrix_int8.hex').read_text().split('\n')
                row = list(text[line])
                v = int(row[column], 16) ^ 8
                row[column] = '%x' % v
                text[line] = ''.join(row)
                (root / d.name / die.name / 'matrix_int8.hex').write_text('\n'.join(text))
                (stage / f'mutant_{a.name}.json').write_text(json.dumps({
                    'layer': layer, 'rank': rank, 'line': line, 'column': column, 'flipped_nibble_bit': 3,
                    'original_sha256': sha(die / 'matrix_int8.hex'),
                    'mutant_sha256': sha(root / d.name / die.name / 'matrix_int8.hex'),
                    'expected': 'actual layer X mismatch at this layer'}, indent=2) + '\n')
        images = root
    layers = []
    for layer in range(a.layers):
        layers.append({'layer': layer, 'image': str(images / f'layer{layer}'),
                       'program': str(banks / 'fused_images' / f'layer{layer}'),
                       'oracle': str(oracle_dir(banks, a.token, layer))})
    emb = a.embedding.resolve()
    tok = emb / 'vectors' / f'token{a.token}'
    spec = {'position': 0, 'epoch': 0, 'layers': layers,
            'evidence_scope': 'HISTORICAL_FUNCTIONAL_HARNESS_ON_CHIP_MODELS_PRESENT',
            'native_qualified': False,
            'required_native_coverage_gate': 'tools/qwen_composed_harness/audit_native_plan.py',
            'actual_stage0': {'program': str(emb / 'embedding_program.hex'), 'program_sha256': sha(emb / 'embedding_program.hex'),
                              'bank': str(emb / 'vectors'), 'bank_sha256': {n: sha(tok / n) for n in ('codes.hex', 'scale.hex')}}}
    stage.mkdir(parents=True, exist_ok=True)
    spec_path = stage / f'spec_{a.name}.json'
    spec_path.write_text(json.dumps(spec, indent=2) + '\n')
    if a.mutant:
        # The mutant image deliberately differs from the reference-bound bytes;
        # write the plan directly (prepare_sequence would refuse it by design).
        out = stage / f'plan_{a.name}'
        out.mkdir()
        (out / 'layers.plan').write_text(''.join(f"{l['layer']} 0 0 {l['image']} {l['program']} {l['oracle']}\n" for l in layers))
    else:
        subprocess.run([sys.executable, str(HERE / 'prepare_sequence.py'), '--spec', str(spec_path),
                        '--out', str(stage / f'plan_{a.name}')], check=True)
    head = stage / 'head'
    if not head.exists():
        for r in range(8):
            img = head / 'image' / f'die{r}'
            prog = head / 'program' / f'die{r}'
            img.mkdir(parents=True)
            prog.mkdir(parents=True)
            src = banks / 'head_images' / f'rank{r}'
            os.symlink(src / 'matrix_int8.hex', img / 'matrix_int8.hex')
            os.symlink(src / 'matrix_scale_bf16.hex', img / 'matrix_scale_bf16.hex')
            os.symlink(a.canonical / 'head_final_norm_crom.hex', img / 'crom.hex')
            os.symlink(a.canonical / f'head_program_rank{r}.hex', prog / 'program.hex')
            os.symlink(a.canonical / f'head_segments_rank{r}.hex', prog / 'segments.hex')
        pins = {str(f): sha(f) for f in sorted(head.rglob('*')) if f.is_file()}
        (head / 'pins.json').write_text(json.dumps(pins, indent=2) + '\n')
    print(stage / f'plan_{a.name}' / 'layers.plan')


if __name__ == '__main__':
    main()
