#!/usr/bin/env python3
"""Fail-closed Qwen3-8B TP2 layer-shard preflight and RTL bit comparison.

Contract: each side writes ctx{context}_L{layer:02d}_D{die}.npz and .json.
The golden JSON pins the shipped config and checkpoint source lock, source files,
and hashes of every array. The RTL JSON pins its sources and the exact golden
input digest. Only independently produced RTL output can yield bit_exact.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
CONFIG = Path('compiler/models/qwen3-8b/config.json')
LOCK = Path('compiler/models/qwen3-8b/checkpoint_source.json')
REQUIRED = ('h_in', 'h_out')


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def array_sha(array: np.ndarray) -> str:
    h = hashlib.sha256()
    h.update(array.dtype.str.encode())
    h.update(json.dumps(array.shape).encode())
    h.update(np.ascontiguousarray(array).tobytes())
    return h.hexdigest()


def pins_valid(pins: object, root: Path, label: str) -> None:
    if not isinstance(pins, dict) or not pins:
        raise ValueError(f'{label}: nonempty source_sha256 required')
    for rel, expected in pins.items():
        path = Path(rel)
        if path.is_absolute() or '..' in path.parts or not path.parts or not isinstance(expected, str):
            raise ValueError(f'{label}: unsafe source pin {rel}')
        if sha(root / path) != expected:
            raise ValueError(f'{label}: stale source pin {rel}')


def read_shard(directory: Path, context: int, layer: int, die: int):
    stem = f'ctx{context}_L{layer:02d}_D{die}'
    meta = json.loads((directory / f'{stem}.json').read_text())
    with np.load(directory / f'{stem}.npz', allow_pickle=False) as archive:
        arrays = {name: archive[name].copy() for name in archive.files}
    return meta, arrays


def check_identity(meta: dict, context: int, layer: int, die: int, label: str) -> None:
    if (meta.get('context'), meta.get('layer'), meta.get('die'), meta.get('tp'),
            meta.get('position')) != (context, layer, die, 2, context - 1):
        raise ValueError(f'{label}: shard identity mismatch')


def validate_golden(directory: Path, context: int, layer: int, die: int,
                    root: Path = ROOT) -> dict:
    config = json.loads((root / CONFIG).read_text())
    if (config['hidden_size'], config['num_hidden_layers'], config['num_attention_heads'],
            config['num_key_value_heads'], config['intermediate_size']) != (4096, 36, 32, 8, 12288):
        raise ValueError('source config is not shipped Qwen3-8B shape')
    meta, arrays = read_shard(directory, context, layer, die)
    check_identity(meta, context, layer, die, 'golden')
    if meta.get('schema') != 'opentallas.qwen-o4-fullshape-shard.v1':
        raise ValueError('golden: wrong schema')
    if not set(REQUIRED) <= arrays.keys():
        raise ValueError('golden: h_in and h_out required')
    for name in REQUIRED:
        if arrays[name].dtype != np.dtype('<f4') or arrays[name].shape != (4096,):
            raise ValueError(f'golden: {name} must be 4096 FP32 elements')
    if meta.get('config_sha256') != sha(root / CONFIG) or meta.get('checkpoint_lock_sha256') != sha(root / LOCK):
        raise ValueError('golden: shipped config/checkpoint lock pin mismatch')
    if meta.get('array_sha256') != {name: array_sha(value) for name, value in arrays.items()}:
        raise ValueError('golden: array digest mismatch')
    pins_valid(meta.get('source_sha256'), root, 'golden')
    return meta


def compare(golden_dir: Path, rtl_dir: Path, context: int, layers: list[int],
            root: Path = ROOT) -> dict:
    if context < 1 or not layers or layers != sorted(set(layers)) or any(x < 0 or x >= 36 for x in layers):
        raise ValueError('context and ordered layer list out of range')
    rows = []
    for layer in layers:
        for die in range(2):
            golden = validate_golden(golden_dir, context, layer, die, root)
            gm, ga = read_shard(golden_dir, context, layer, die)
            rm, ra = read_shard(rtl_dir, context, layer, die)
            check_identity(rm, context, layer, die, 'RTL')
            if rm.get('golden_input_sha256') != golden['array_sha256']['h_in']:
                raise ValueError('RTL: golden input digest mismatch')
            if type(rm.get('cycles')) is not int or rm['cycles'] <= 0:
                raise ValueError('RTL: positive simulated cycles required')
            pins_valid(rm.get('source_sha256'), root, 'RTL')
            if not set(ga) <= set(ra):
                raise ValueError(f'RTL: missing arrays {sorted(set(ga) - set(ra))}')
            for name, expected in ga.items():
                actual = ra[name]
                if expected.dtype != actual.dtype or expected.shape != actual.shape:
                    raise ValueError(f'L{layer} D{die} {name}: dtype/shape mismatch')
                if expected.tobytes() != actual.tobytes():
                    raise ValueError(f'L{layer} D{die} {name}: bit mismatch')
            rows.append({'layer': layer, 'die': die, 'cycles': rm['cycles'],
                         'matched_arrays': sorted(ga), 'rtl_source_sha256': rm['source_sha256']})
    return {'status': 'bit_exact_supplied_shards', 'context': context, 'shards': rows,
            'claim_boundary': 'Layer-shard RTL outputs only; no full token, full model, or throughput pass.'}


def preflight(golden_dir: Path, rtl_dir: Path, context: int, layers: list[int],
              root: Path = ROOT) -> dict:
    blockers = []
    for layer in layers:
        for die in range(2):
            stem = f'ctx{context}_L{layer:02d}_D{die}'
            for label, directory in (('golden', golden_dir), ('RTL', rtl_dir)):
                for suffix in ('.json', '.npz'):
                    if not (directory / (stem + suffix)).is_file():
                        blockers.append(f'{label} missing {stem + suffix}')
    checkpoint_dir = root / 'build/models/qwen3-8b'
    lock = json.loads((root / LOCK).read_text())
    for item in lock['expected_files']:
        if item['path'].endswith('.safetensors') and not (checkpoint_dir / item['path']).is_file():
            blockers.append(f"shipped checkpoint missing {item['path']}")
    return {'status': 'blocked' if blockers else 'ready_to_compare', 'blockers': blockers,
            'claim_boundary': 'Preflight checks presence only; it does not validate bit exactness.'}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--golden-dir', type=Path, required=True)
    ap.add_argument('--rtl-dir', type=Path, required=True)
    ap.add_argument('--context', type=int, required=True)
    ap.add_argument('--layers', required=True, help='comma-separated layer numbers')
    ap.add_argument('--source-root', type=Path, default=ROOT)
    ap.add_argument('--preflight', action='store_true')
    ap.add_argument('--output', type=Path)
    args = ap.parse_args()
    layers = [int(x) for x in args.layers.split(',')]
    result = (preflight(args.golden_dir, args.rtl_dir, args.context, layers, args.source_root)
              if args.preflight else compare(args.golden_dir, args.rtl_dir, args.context, layers, args.source_root))
    if args.output:
        args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
    if result['status'] == 'blocked':
        raise SystemExit(2)


if __name__ == '__main__':
    main()
