#!/usr/bin/env python3
"""Source manifest for S81 die generations (S-DIE 2026-10-15).

Hole closed: run scripts hashed only tools/ rtl/ physical/, so the contract that a
generation actually loaded (results/arch/hier_contract_1011/*.json, the opts file,
the canonical layout) was never source-bound. GEN16/screen14 ran on contract
VERSION 18 while declaring a v19 source and nothing detected it.

  tree   --root SRC --out M.json [--extra FILE ...]  hash a copied source tree
  git    --commit C --out M.json                      expected hashes at a commit
  check  --manifest M.json --expect E.json [--require FILE ...]

Every --require path (the generator's input files) must be present in BOTH the
manifest and the expected one with equal sha256, otherwise check exits 1.
"""
import argparse, hashlib, json, subprocess, sys
from pathlib import Path

BASES = ('tools', 'rtl', 'physical', 'results/arch', 'results/physical/die_iter_1012/s81')


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def tree(root, extra=()):
    root = Path(root).resolve(); out = {}
    for base in BASES:
        b = root / base
        if not b.exists():
            continue
        for p in b.rglob('*'):
            if p.is_file() and '__pycache__' not in p.parts:
                out[str(p.relative_to(root))] = sha(p)
    for e in extra:
        p = Path(e); p = p if p.is_absolute() else root / p
        if p.is_file():
            key = str(p.relative_to(root)) if p.resolve().is_relative_to(root) else str(p)
            out[key] = sha(p)
    return out


def from_git(commit, repo='.'):
    files = subprocess.run(['git', '-C', repo, 'ls-tree', '-r', '--name-only', commit, '--', *BASES],
                           check=True, capture_output=True, text=True).stdout.split('\n')
    files = [f for f in files if f]
    out = {}
    proc = subprocess.Popen(['git', '-C', repo, 'cat-file', '--batch'], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    for f in files:
        proc.stdin.write(f'{commit}:{f}\n'.encode()); proc.stdin.flush()
        hdr = proc.stdout.readline().split()
        if len(hdr) < 3 or hdr[1] != b'blob':
            continue
        data = proc.stdout.read(int(hdr[2])); proc.stdout.read(1)
        out[f] = hashlib.sha256(data).hexdigest()
    proc.stdin.close(); proc.wait()
    return out


def check(manifest, expect, require=()):
    bad = []
    for f in require:
        a, b = manifest.get(f), expect.get(f)
        if a is None or b is None or a != b:
            bad.append(dict(path=f, tree=a, expected=b))
    common = set(manifest) & set(expect)
    drift = sorted(f for f in common if manifest[f] != expect[f])
    return dict(verdict='FAIL' if bad else 'PASS', required_mismatch=bad,
                drift_count=len(drift), drift_first=drift[:50],
                contract_drift=[f for f in drift if f.startswith('results/arch/')])


def main():
    ap = argparse.ArgumentParser(); sp = ap.add_subparsers(dest='cmd', required=True)
    t = sp.add_parser('tree'); t.add_argument('--root', required=True); t.add_argument('--out', required=True); t.add_argument('--extra', nargs='*', default=[])
    g = sp.add_parser('git'); g.add_argument('--commit', required=True); g.add_argument('--repo', default='.'); g.add_argument('--out', required=True)
    c = sp.add_parser('check'); c.add_argument('--manifest', required=True); c.add_argument('--expect', required=True); c.add_argument('--require', nargs='*', default=[])
    a = ap.parse_args()
    if a.cmd == 'tree':
        Path(a.out).write_text(json.dumps(tree(a.root, a.extra), indent=1, sort_keys=True)); return 0
    if a.cmd == 'git':
        Path(a.out).write_text(json.dumps(from_git(a.commit, a.repo), indent=1, sort_keys=True)); return 0
    r = check(json.loads(Path(a.manifest).read_text()), json.loads(Path(a.expect).read_text()), a.require)
    print(json.dumps(r, indent=1)); return 0 if r['verdict'] == 'PASS' else 1



def generator_inputs(root, opts):
    """Repo-relative input files named by generator options (+ env LEF overrides)."""
    import os
    root = Path(root).resolve(); found = set()
    vals = list(opts.values()) + [v for k, v in os.environ.items() if k.startswith('OT_S81_')]
    for v in vals:
        for s in (v if isinstance(v, (list, tuple)) else [v]):
            if not isinstance(s, (str, Path)) or not str(s) or len(str(s)) > 4096:
                continue
            p = Path(s); p = p if p.is_absolute() else root / p
            try:
                if p.is_file():
                    found.add(str(p.resolve().relative_to(root)) if p.resolve().is_relative_to(root) else str(p))
            except OSError:
                pass
    return sorted(found)


def contract_record(root, contract):
    if not contract:
        return None
    p = Path(contract); p = p if p.is_absolute() else Path(root) / p
    d = json.loads(p.read_text())
    return dict(path=str(contract), sha256=sha(p), version=d.get('version'), updated=d.get('updated'))


if __name__ == '__main__':
    sys.exit(main())
