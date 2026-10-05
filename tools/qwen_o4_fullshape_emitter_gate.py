#!/usr/bin/env python3
"""Recheck pinned real-checkpoint Qwen TP2 image/ISA sample artifacts."""
import argparse
import hashlib
import json
from pathlib import Path

from hdc_qwen_layer0_rom import pinned_snapshot, verify_sample

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def check_vocab(directory, kind, snapshot):
    directory = Path(directory)
    path = directory / f'{kind}_window.json'
    meta = json.loads(path.read_text())
    if meta['kind'] != kind or meta['checkpoint_revision'] != snapshot.name:
        raise ValueError(f'{kind} window source mismatch')
    for rel, sha in meta['source_sha256'].items():
        if digest(ROOT / rel) != sha:
            raise ValueError(f'{kind} stale source pin: {rel}')
    for name, sha in meta['image_sha256'].items():
        if digest(directory / name) != sha:
            raise ValueError(f'{kind} image digest mismatch: {name}')
    return {'kind': kind, 'global_start': meta['global_start'], 'rows': meta['rows'],
            'manifest_sha256': digest(path), 'image_sha256': meta['image_sha256']}


def gate(snapshot, layer0_d0, layer0_d1, layer35_d0, embed_token0, embed_last, head_last):
    pinned_snapshot(snapshot)
    rows = []
    for layer, die, directory in ((0, 0, layer0_d0), (0, 1, layer0_d1), (35, 0, layer35_d0)):
        check = verify_sample(snapshot, directory, die, 8, layer)
        manifest = Path(directory) / f'layer{layer}_rom.json'
        rows.append({'layer': layer, 'die': die, 'codes_checked': check['codes_checked'],
                     'manifest_sha256': digest(manifest)})
    windows = [check_vocab(embed_token0, 'embedding', snapshot),
               check_vocab(embed_last, 'embedding', snapshot),
               check_vocab(head_last, 'lm_head', snapshot)]
    if [(x['kind'], x['global_start']) for x in windows] != [
            ('embedding', 0), ('embedding', 151935), ('lm_head', 151935)]:
        raise ValueError('vocabulary endpoint windows missing')
    return {'schema': 'opentallas.qwen-o4-fullshape-emitter-gate.v1',
            'status': 'exact_sampled_real_checkpoint_images',
            'checkpoint_revision': snapshot.name,
            'checkpoint_lock_sha256': digest(ROOT / 'compiler/models/qwen3-8b/checkpoint_source.json'),
            'sampled_layer_images': rows, 'vocabulary_windows': windows,
            'total_code_addresses_checked': sum(x['codes_checked'] for x in rows),
            'claim_boundary': 'Sampled shipped layer ROM/ISA and vocabulary images only; no RTL layer or full token pass.'}


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    for name in ('snapshot', 'layer0_d0', 'layer0_d1', 'layer35_d0',
                 'embed_token0', 'embed_last', 'head_last', 'output'):
        ap.add_argument('--' + name.replace('_', '-'), type=Path, required=True)
    args = ap.parse_args()
    result = gate(args.snapshot, args.layer0_d0, args.layer0_d1, args.layer35_d0,
                  args.embed_token0, args.embed_last, args.head_last)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'status': result['status'], 'codes_checked': result['total_code_addresses_checked']}))


if __name__ == '__main__':
    main()
