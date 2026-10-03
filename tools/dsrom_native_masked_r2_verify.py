#!/usr/bin/env python3
"""Source-only loader and cache-only projection; never read Python bytecode."""
import hashlib
import json
import types
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT/'results/uarch/dsrom_native_masked_backend_r2_20261003'


def cache_path(path):
    p = Path(path)
    return '__pycache__' in p.parts and p.suffix == '.pyc'


def source_module(path):
    path = Path(path)
    module = types.ModuleType(path.stem)
    module.__file__ = str(path)
    exec(compile(path.read_bytes(), str(path), 'exec'), module.__dict__)
    return module


def verify_receipt(root, hashes):
    checked = []
    excluded = []
    for relative, digest in hashes.items():
        if cache_path(relative):
            excluded.append(relative)
            continue
        path = Path(root)/relative
        if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise ValueError('Artifact drift: '+relative)
        checked.append(relative)
    return dict(checked=checked, excluded_caches=excluded)


def verify():
    manifest = json.loads((BASE/'source_manifest.json').read_text())
    projection = verify_receipt(ROOT, manifest)
    historical = json.loads((ROOT/'results/uarch/dsrom_native_masked_backend_prepare_20261003/validation.json').read_text())
    projection['historical_receipt_projection'] = verify_receipt(ROOT, historical['artifact_hashes'])
    # Load the original arithmetic transcription from bytes, including its
    # nested codec, bypassing both cache reads and cache writes.
    codec = source_module(ROOT/'results/uarch/dsrom_native_masked_backend_prepare_20261003/inputs/codec_model.py')
    predecessor = source_module(ROOT/'tools/dsrom_native_masked_backend_prepare.py')
    predecessor.codec = lambda: source_module(ROOT/'results/uarch/dsrom_native_masked_backend_prepare_20261003/inputs/codec_model.py')
    if predecessor.build() != json.loads((BASE/'inputs/r1_model.json').read_text()):
        raise ValueError('Source-only predecessor model mismatch')
    if codec.decode64(codec.encode64(0xFEDCBA9876543210)) != (0xFEDCBA9876543210, False, False):
        raise ValueError('Source-only nested codec mismatch')
    return projection


if __name__ == '__main__':
    print(json.dumps(verify(), indent=2, sort_keys=True))
