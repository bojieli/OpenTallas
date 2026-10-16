#!/usr/bin/env python3
"""Freeze a Git tree and verify actual snapshot bytes before geometry reuse."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess


def digest(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as stream:
        while chunk := stream.read(1024 * 1024):
            value.update(chunk)
    return value.hexdigest()


def make(repo, commit):
    commit = subprocess.check_output(['git', '-C', str(repo), 'rev-parse', commit], text=True).strip()
    tree = subprocess.check_output(['git', '-C', str(repo), 'rev-parse', commit + '^{tree}'], text=True).strip()
    raw = subprocess.check_output(['git', '-C', str(repo), 'ls-tree', '-rlz', commit])
    files = []
    for entry in raw.split(b'\0'):
        if not entry:
            continue
        head, path = entry.split(b'\t', 1)
        mode, kind, blob, size = head.decode().split()
        if kind != 'blob':
            raise ValueError('unsupported Git tree entry: ' + head.decode())
        files.append(dict(path=path.decode(), mode=mode, git_blob=blob, bytes=int(size)))
    # Git LFS stores a small Git pointer; the actual input is its SHA256 object.
    candidates = [item for item in files if item['mode'] != '120000' and item['bytes'] <= 256]
    batch = subprocess.run(['git', '-C', str(repo), 'cat-file', '--batch'],
                           input=''.join(item['git_blob'] + '\n' for item in candidates).encode(),
                           stdout=subprocess.PIPE, check=True).stdout
    position = 0
    for item in candidates:
        end = batch.index(b'\n', position)
        header = batch[position:end].decode().split()
        size = int(header[2])
        payload = batch[end+1:end+1+size]
        position = end + 1 + size + 1
        if payload.startswith(b'version https://git-lfs.github.com/spec/v1\n'):
            fields = dict(line.split(' ', 1) for line in payload.decode().splitlines())
            item['lfs_sha256'] = fields['oid'].removeprefix('sha256:')
            item['bytes'] = int(fields['size'])
    return dict(schema='opentallas.source-tree-manifest.v1', source_commit=commit,
                git_tree=tree, files=files, external_files=[])


def verify(root, manifest):
    root = root.resolve()
    expected_paths = {item['path'] for item in manifest['files']}
    for directory, folders, names in os.walk(root, followlinks=False):
        folders[:] = [name for name in folders if name not in ('.git', '__pycache__')]
        for name in names:
            relative = str((Path(directory) / name).relative_to(root))
            if relative not in expected_paths and relative != 'SOURCE_SHA':
                raise ValueError('untracked input in source snapshot: ' + relative)
    checked_bytes = 0
    for entry in manifest['files']:
        path = root / entry['path']
        if not path.parent.resolve().is_relative_to(root):
            raise ValueError('source file escapes snapshot: ' + entry['path'])
        value = hashlib.sha1()
        if entry['mode'] == '120000':
            if not path.is_symlink():
                raise ValueError('source symlink missing: ' + entry['path'])
            payload = os.fsencode(os.readlink(path))
            value.update(b'blob ' + str(len(payload)).encode() + b'\0' + payload)
            # Targets outside the snapshot require an explicit frozen target inventory.
            target = path.resolve()
            if not target.is_relative_to(root):
                extras = [Path(item['path']).resolve() for item in manifest['external_files']]
                if not any(target == ext or target in ext.parents for ext in extras):
                    raise ValueError('external symlink target is not inventoried: ' + entry['path'])
        else:
            if path.is_symlink() or not path.is_file():
                raise ValueError('source file missing or replaced by symlink: ' + entry['path'])
            size = path.stat().st_size
            value = hashlib.sha256() if entry.get('lfs_sha256') else value
            if not entry.get('lfs_sha256'):
                value.update(b'blob ' + str(size).encode() + b'\0')
            with path.open('rb') as stream:
                while chunk := stream.read(1024 * 1024):
                    value.update(chunk)
            checked_bytes += size
        if value.hexdigest() != entry.get('lfs_sha256', entry['git_blob']):
            raise ValueError('actual source bytes differ from Git tree: ' + entry['path'])
    for item in manifest['external_files']:
        if digest(item['path']) != item['sha256']:
            raise ValueError('external source bytes differ: ' + item['path'])
    return dict(files=len(manifest['files']), bytes=checked_bytes,
                external_files=len(manifest['external_files']), git_tree=manifest['git_tree'])


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest='mode', required=True)
    create = sub.add_parser('make')
    create.add_argument('--repo', type=Path, required=True)
    create.add_argument('--commit', required=True)
    create.add_argument('--out', type=Path, required=True)
    check = sub.add_parser('verify')
    check.add_argument('--root', type=Path, required=True)
    check.add_argument('--manifest', type=Path, required=True)
    args = ap.parse_args()
    if args.mode == 'make':
        args.out.write_text(json.dumps(make(args.repo, args.commit), separators=(',', ':')) + '\n')
    else:
        print(json.dumps(verify(args.root, json.loads(args.manifest.read_text()))))


if __name__ == '__main__':
    main()
