#!/usr/bin/env python3
"""package.py PLAN_DIR BASE_DIR DEST: copy into DEST every file of PLAN_DIR (top level + cores/) whose content differs from
BASE_DIR (the unpacked d44t plan dir) -- die_plan.json and every file > 200 kB gzipped (mtime 0, byte-reproducible)."""
import gzip, hashlib, os, sys, shutil
from pathlib import Path
p, b, d = map(Path, sys.argv[1:4]); d.mkdir(parents=True, exist_ok=True)
h = lambda f: hashlib.sha256(f.read_bytes()).hexdigest()
n = 0
for sub in ('', 'cores'):
    for f in sorted((p / sub).iterdir() if sub else p.iterdir()):
        if f.is_dir() or f.name in ('die_plan.sha256',):
            continue
        q = b / sub / f.name
        if q.exists() and h(q) == h(f):
            continue
        (d / sub).mkdir(exist_ok=True)
        if f.name == 'die_plan.json' or f.stat().st_size > 200_000:
            with open(d / sub / (f.name + '.gz'), 'wb') as o, gzip.GzipFile(fileobj=o, mode='wb', mtime=0, filename='') as g:
                g.write(f.read_bytes())
        else:
            shutil.copyfile(f, d / sub / f.name)
        n += 1
print(n, 'files')
