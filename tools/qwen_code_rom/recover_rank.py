#!/usr/bin/env python3
"""Regenerate one complete native TP8 code-ROM rank from the pinned checkpoint.

Checkpoint bytes are validated once across concurrent rank jobs. The cache is
valid only while every selected file's inode, size, mtime and ctime match; every
image emission checks that fingerprint again. Arithmetic and ROM packing use
the existing released image generators without modification.
"""
import argparse
import fcntl
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))


def fingerprint(snapshot, lock):
    result = {}
    for entry in lock['expected_files']:
        name = entry['path']
        if not (name.endswith('.safetensors') or name in ('config.json', lock['checkpoint_index'])):
            continue
        stat = (snapshot / name).stat()
        result[name] = [stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns]
    return result


def validate_once(snapshot, lock_path, validator):
    lock = json.loads(lock_path.read_text())
    stamp = fingerprint(snapshot, lock)
    key = dict(snapshot=str(snapshot.resolve()),
               source_lock_sha256=hashlib.sha256(lock_path.read_bytes()).hexdigest(), files=stamp)
    cache = snapshot.parent / 'native_image_validation.json'
    with cache.with_suffix('.lock').open('a') as stream:
        fcntl.flock(stream, fcntl.LOCK_EX)
        old = json.loads(cache.read_text()) if cache.is_file() else None
        if old != key:
            validator(snapshot)
            if fingerprint(snapshot, lock) != stamp:
                raise ValueError('checkpoint changed during source validation')
            temp = cache.with_name(cache.name + f'.{os.getpid()}.tmp')
            temp.write_text(json.dumps(key, sort_keys=True) + '\n')
            temp.replace(cache)
            print('CHECKPOINT_VALIDATED', flush=True)
        else:
            print('CHECKPOINT_VALIDATION_REUSED', flush=True)

    def guard(path):
        if Path(path).resolve() != snapshot.resolve() or fingerprint(snapshot, lock) != stamp:
            raise ValueError('checkpoint changed after source validation')
        return lock
    return guard


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--snapshot', type=Path, required=True)
    parser.add_argument('--rank', type=int, choices=range(8), required=True)
    parser.add_argument('--banks', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--logs', type=Path, required=True)
    args = parser.parse_args()
    os.environ['QWEN_O4_TP'] = '8'
    os.environ['QWEN_O4_GROUPS'] = '3072'
    import hdc_qwen_layer0_rom_w12 as layer
    import qwen_o4_head_rom_w12 as head
    args.logs.mkdir(parents=True, exist_ok=True)
    guard = validate_once(args.snapshot, layer.LOCK, layer.pinned_snapshot)
    layer.pinned_snapshot = guard
    head.pinned_snapshot = guard
    for index in range(36):
        destination = args.banks / f'images/layer{index}/die{args.rank}'
        manifest = destination / f'layer{index}_rom.json'
        if manifest.is_file():
            guard(args.snapshot)
            print('EXISTING_LAYER', index, args.rank, flush=True)
        else:
            record = layer.emit(args.snapshot, destination, args.rank, index, True)
            print('LAYER_EMITTED', index, args.rank, record['matrix_words'], flush=True)
    destination = args.banks / f'head_images/rank{args.rank}'
    if not (destination / 'head_rom.json').is_file():
        record = head.emit(args.snapshot, destination, args.rank)
        print('HEAD_EMITTED', args.rank, record['code_words'], flush=True)
    guard(args.snapshot)
    with (args.logs / 'code_masks.log').open('w') as stream:
        subprocess.run([sys.executable, str(ROOT / 'tools/qwen_code_rom/build.py'),
                        '--banks', str(args.banks), '--out', str(args.out),
                        '--ranks', str(args.rank), '--jobs', '1'],
                       stdout=stream, stderr=subprocess.STDOUT, check=True)
    print('RANK_CODE_MASKS_COMPLETE', args.rank, args.out, flush=True)


if __name__ == '__main__':
    main()
