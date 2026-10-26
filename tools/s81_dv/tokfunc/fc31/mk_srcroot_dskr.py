#!/usr/bin/env python3
"""TOK-DS 10-25 (dskr): materialise the S81 selected source root of the deskew cut vehicles from git objects only.
root30 (the 10-22 cap30 bind source root that the fc30/fc31 kits and layer programmes were built against) minus tools/ is
listed blob-by-blob in results/token_pass/tokds_dskr_1025/root30_blobs.txt ("<git blob> <mode> <path>"; every blob must be
in this repository, else FAIL), plus the one file no commit holds (root30_cells_used.v, kept as data next to the list).
Then tools/ := tools/ of THIS checkout and rtl/dsrom_sys/s81_dv/slice/ot_s81sl_xrt.sv := the file at THIS checkout (the
committed NORM-DESKEW XRT; replaces the lost uncommitted ec43bbd4 one). Writes <out>/srcroot.json (commit, per-file blobs).
  mk_srcroot_dskr.py --out <fresh dir>
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

R = Path(__file__).resolve().parents[4]
D = R / 'results/token_pass/tokds_dskr_1025'
XRT = 'rtl/dsrom_sys/s81_dv/slice/ot_s81sl_xrt.sv'


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out', required=True)
    o = Path(ap.parse_args().out).resolve()
    if o.exists():
        sys.exit('mk_srcroot: output exists (fresh dirs only)')
    rows = [ln.split(' ', 2) for ln in (D / 'root30_blobs.txt').read_text().splitlines() if ln.strip()]
    p = subprocess.Popen(['git', '-C', str(R), 'cat-file', '--batch'], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    for blob, mode, path in rows:
        p.stdin.write((blob + '\n').encode()); p.stdin.flush()
        hdr = p.stdout.readline().decode().split()
        if len(hdr) != 3 or hdr[1] != 'blob':
            sys.exit(f'mk_srcroot: FAIL blob {blob} for {path} not in this repository ({hdr})')
        data = p.stdout.read(int(hdr[2])); p.stdout.read(1)
        f = o / path
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_bytes(data)
        os.chmod(f, 0o755 if mode == '755' else 0o644)
    p.stdin.close(); p.wait()
    shutil.copy(D / 'root30_cells_used.v', o / 'cells_used.v')
    shutil.copytree(R / 'tools', o / 'tools', symlinks=True, ignore=shutil.ignore_patterns('__pycache__'))
    shutil.copy(R / XRT, o / XRT)
    head = subprocess.check_output(['git', '-C', str(R), 'rev-parse', 'HEAD'], text=True).strip()
    dirty = subprocess.check_output(['git', '-C', str(R), 'status', '--porcelain', '--untracked-files=no'], text=True).strip()
    xb = subprocess.check_output(['git', '-C', str(R), 'hash-object', str(R / XRT)], text=True).strip()
    (o / 'srcroot.json').write_text(json.dumps(dict(schema='opentallas.tok_ds.dskr_srcroot.v1', commit=head, dirty=bool(dirty),
        root30_blobs=len(rows), extra_data=['cells_used.v'], tools='this checkout', xrt_blob=xb), indent=1) + '\n')
    print(f'SRCROOT {o} commit {head[:10]}{" DIRTY" if dirty else ""}: {len(rows)} root30 blobs + cells_used.v + tools + xrt {xb[:10]}')


if __name__ == '__main__':
    main()
