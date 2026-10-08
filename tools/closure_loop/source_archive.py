#!/usr/bin/env python3
"""Check an explicit runner inventory against a pinned, compact git archive.

This checks declared dependencies, not automatic transitive dependency closure.
Run each candidate's --prepare-only mode in the extracted archive as a separate
step. Runtime files are checked on the execution host with --runtime-only; they
are never copied into the archive. A receipt is not admission or a build verdict.

Inventory JSON: {"paths": ["tools", "rtl", "physical", "Makefile"],
 "extra_paths": ["compiler/models/example.json"],
 "required_files": ["tools/runner.py", "physical/macro.v"],
 "runtime_files": [{"path": "/existing/checkpoint", "sha256": "..."}]}
"""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import subprocess
import tarfile
import tempfile

DEFAULT_SRC_PATHS = ["tools", "rtl", "physical", "Makefile"]


def repo_path(value):
    if not isinstance(value, str) or not value or value.startswith('-'):
        raise ValueError(f"Invalid repository path: {value!r}")
    p = PurePosixPath(value)
    if p.is_absolute() or '..' in p.parts or str(p) != value or value == '.':
        raise ValueError(f"Expected a literal relative repository path: {value!r}")
    return value


def check_runtime(rows):
    receipts = []
    for row in rows:
        p = Path(row['path'])
        expected = row['sha256']
        if not p.is_absolute() or len(expected) != 64 or any(c not in '0123456789abcdef' for c in expected):
            raise ValueError('Runtime dependency needs an absolute path and lowercase SHA256')
        h = hashlib.sha256()
        with p.open('rb') as f:
            before = p.stat()
            while chunk := f.read(1024 * 1024):
                h.update(chunk)
            after = p.stat()
        if (before.st_ino, before.st_size, before.st_mtime_ns) != (after.st_ino, after.st_size, after.st_mtime_ns):
            raise ValueError(f'Runtime dependency changed during verification: {p}')
        if h.hexdigest() != expected:
            raise ValueError(f'Runtime dependency hash mismatch: {p}')
        receipts.append(dict(path=str(p), sha256=expected, bytes=after.st_size))
    return receipts


def build_archive(repo, commit, inventory, destination):
    paths = list(dict.fromkeys(repo_path(p) for p in
                 inventory.get('paths', DEFAULT_SRC_PATHS) + inventory.get('extra_paths', [])))
    required = [repo_path(p) for p in inventory['required_files']]
    if not paths or not required:
        raise ValueError('Archive paths and explicit required_files must be nonempty')
    def git(*args):
        return subprocess.check_output(['git', '-C', str(repo), *args], text=True).strip()
    full = git('rev-parse', '--verify', f'{commit}^{{commit}}')
    # Literal path semantics: git archive pathspec magic is not supported here.
    for p in paths:
        git('cat-file', '-e', f'{full}:{p}')
    with tempfile.TemporaryFile() as archive:
        subprocess.run(['git', '--literal-pathspecs', '-C', str(repo), 'archive',
                        '--format=tar', full, '--', *paths], stdout=archive, check=True)
        archive.seek(0)
        with tarfile.open(fileobj=archive, mode='r:') as tar:
            members = {m.name: m for m in tar.getmembers()}
            missing = [p for p in required if p not in members or not members[p].isfile()]
            if missing:
                raise ValueError('Required files absent from actual archive: ' + ', '.join(missing))
            pins = {}
            for p in required:
                h = hashlib.sha256()
                with tar.extractfile(members[p]) as f:
                    while chunk := f.read(1024 * 1024):
                        h.update(chunk)
                pins[p] = h.hexdigest()
        archive.seek(0)
        h = hashlib.sha256()
        # Exclusive creation preserves earlier archive/failure evidence.
        with Path(destination).open('xb') as out:
            while chunk := archive.read(1024 * 1024):
                h.update(chunk)
                out.write(chunk)
    return dict(commit=full, paths=paths, required_sha256=pins,
                archive_sha256=h.hexdigest(), archive=str(destination),
                scope='Declared source inventory only; run candidate preparation and target runtime checks separately',
                runtime_files_pending=inventory.get('runtime_files', []))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--inventory', required=True, type=Path)
    p.add_argument('--repo', type=Path, default=Path.cwd())
    p.add_argument('--commit')
    p.add_argument('--output', type=Path)
    p.add_argument('--runtime-only', action='store_true')
    a = p.parse_args()
    inventory = json.loads(a.inventory.read_text())
    if a.runtime_only:
        print(json.dumps({'runtime_verified': check_runtime(inventory['runtime_files'])}, indent=2))
    else:
        if not a.commit or not a.output:
            p.error('--commit and --output are required for archive creation')
        print(json.dumps(build_archive(a.repo, a.commit, inventory, a.output), indent=2))


if __name__ == '__main__':
    main()
