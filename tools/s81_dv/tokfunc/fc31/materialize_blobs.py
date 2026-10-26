#!/usr/bin/env python3
"""TOK-DS 10-25 (dskr): write a file tree from git objects only. LIST lines are "<git blob> <mode 644|755> <path>"; a blob
missing from this repository is taken from DATA/<path> (committed data next to the list) and must hash to the listed blob;
anything else FAILs. Used for the dskr vehicle inputs (inputs_blobs.txt + inputs_data/) so no evidence reads out-of-repo files.
  materialize_blobs.py --list <blob list> [--data <dir>] --out <fresh dir>
"""
import argparse
import os
import subprocess
import sys
from pathlib import Path

R = Path(__file__).resolve().parents[4]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--list', required=True)
    ap.add_argument('--data')
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    o = Path(a.out).resolve()
    if o.exists():
        sys.exit('materialize: output exists (fresh dirs only)')
    rows = [ln.split(' ', 2) for ln in Path(a.list).read_text().splitlines() if ln.strip()]
    p = subprocess.Popen(['git', '-C', str(R), 'cat-file', '--batch'], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    n_git = n_data = 0
    for blob, mode, path in rows:
        p.stdin.write((blob + '\n').encode()); p.stdin.flush()
        hdr = p.stdout.readline().decode().split()
        if len(hdr) == 3 and hdr[1] == 'blob':
            data = p.stdout.read(int(hdr[2])); p.stdout.read(1); n_git += 1
        else:
            src = Path(a.data or '/nonexistent') / path
            if not src.is_file():
                sys.exit(f'materialize: FAIL {path}: blob {blob} not in repo and no data file')
            got = subprocess.check_output(['git', 'hash-object', str(src)], text=True).strip()
            if got != blob:
                sys.exit(f'materialize: FAIL {path}: data file blob {got} != listed {blob}')
            data = src.read_bytes(); n_data += 1
        f = o / path
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_bytes(data)
        os.chmod(f, 0o755 if mode == '755' else 0o644)
    p.stdin.close(); p.wait()
    print(f'MATERIALIZED {o}: {n_git} git blobs + {n_data} committed data files')


if __name__ == '__main__':
    main()
