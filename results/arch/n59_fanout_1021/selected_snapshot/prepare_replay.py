#!/usr/bin/env python3
"""Verify the frozen selected source and prepare a separate replay tree; runs no EDA."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

package = Path(__file__).resolve().parent
manifest = json.loads((package / 'MANIFEST.json').read_text())
ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument('--dest', type=Path, help='new or empty destination outside the package')
ap.add_argument('--verify-tree', type=Path, help='also verify a previously prepared replay tree')
args = ap.parse_args()

def verify(root):
    for row in manifest['files']:
        p = root / row['path']
        if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest() != row['sha256']:
            raise SystemExit('N59_SNAPSHOT_HASH_MISMATCH ' + str(p))
    count = sum(r['role'] == 'selected_source' for r in manifest['files'])
    if count != 10:
        raise SystemExit('N59_SNAPSHOT_SOURCE_COUNT_MISMATCH')

verify(package / 'payload')
if args.verify_tree:
    verify(args.verify_tree.resolve())
if args.dest:
    dest = args.dest.resolve()
    if dest == package or package in dest.parents:
        raise SystemExit('N59_SNAPSHOT_DEST_MUST_BE_OUTSIDE_PACKAGE')
    if dest.exists() and any(dest.iterdir()):
        raise SystemExit('N59_SNAPSHOT_DEST_MUST_BE_EMPTY')
    dest.mkdir(parents=True, exist_ok=True)
    for row in manifest['files']:
        p = dest / row['path']
        p.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(package / 'payload' / row['path'], p)
    verify(dest)
    (dest / 'N59_FROZEN_PROFILE.json').write_text(json.dumps(manifest['profile'], indent=2) + '\n')
    print('N59_REPLAY_TREE_READY ' + str(dest))
print('N59_SNAPSHOT_HASH_PASS selected_sources=10 assets=' + str(len(manifest['files'])))
