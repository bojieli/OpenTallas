#!/usr/bin/env python3
"""Recover the released Qwen checkpoint files required by the native ROM emitters.

Use only the repository's immutable source lock; resume interrupted downloads,
check every size/hash, and leave any failed download available for diagnosis.
"""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def digest(path):
    sha = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(8 << 20), b''):
            sha.update(block)
    return sha.hexdigest()


def recover(lock_path, destination):
    lock = json.loads(lock_path.read_text())
    revision = lock['revision']
    snapshot = destination / revision
    snapshot.mkdir(parents=True, exist_ok=True)
    selected = [entry for entry in lock['expected_files'] if
                entry['path'].endswith('.safetensors') or entry['path'] in
                ('config.json', lock['checkpoint_index'])]
    for entry in selected:
        name = entry['path']
        path = snapshot / name
        if path.is_file():
            if path.stat().st_size != entry['size_bytes'] or digest(path) != entry['sha256']:
                raise ValueError(f'existing checkpoint does not match source lock: {path}')
            print('PRESENT', name, entry['size_bytes'], flush=True)
            continue
        partial = path.with_name(path.name + '.part')
        url = f"https://huggingface.co/{lock['repository']}/resolve/{revision}/{name}"
        subprocess.run(['curl', '--fail', '--location', '--retry', '5', '--retry-all-errors',
                        '--continue-at', '-', '--output', str(partial), url], check=True)
        if partial.stat().st_size != entry['size_bytes'] or digest(partial) != entry['sha256']:
            raise ValueError(f'download does not match source lock; preserved at {partial}')
        partial.rename(path)
        print('RECOVERED', name, entry['size_bytes'], flush=True)
    receipt = {'source_lock_sha256': digest(lock_path), 'repository': lock['repository'],
               'revision': revision, 'snapshot': str(snapshot), 'files': selected,
               'scope': 'Released checkpoint source recovery only; no RTL or token verdict.'}
    (destination / 'checkpoint_recovery.json').write_text(json.dumps(receipt, indent=2) + '\n')
    return snapshot


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--lock', type=Path, default=ROOT / 'compiler/models/qwen3-8b/checkpoint_source.json')
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    print(recover(args.lock, args.out))
