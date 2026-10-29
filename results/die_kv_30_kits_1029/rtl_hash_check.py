#!/usr/bin/env python3
"""DIE-KV-30-KITS: verify each partition kit's rtl/ equals the strict bind27f kit-RTL export (byte sha256)."""
import hashlib, json, sys
from pathlib import Path
B = Path(sys.argv[1])   # .../bind_fast/kit_rtl
K = Path(sys.argv[2])   # .../codex-kv-partition-0822/kits
types = sys.argv[3].split(',')
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
out = {}
for t in types:
    f = B / t / 'kit_rtl.f'
    srcs = [l.strip() for l in f.read_text().splitlines() if l.strip() and not l.startswith(('+', '-', '//'))]
    kit_rtl = K / t / 'rtl'
    kit_files = {p.name: p for p in kit_rtl.glob('*') if p.is_file()}
    rows, bad = [], []
    for s in srcs:
        n = Path(s).name
        ks = sha(kit_files[n]) if n in kit_files else None
        ss = sha(s)
        rows.append((n, ss[:16], (ks or 'MISSING')[:16]))
        if ks != ss: bad.append(n)
    extra = sorted(set(kit_files) - {Path(s).name for s in srcs})
    out[t] = dict(kit_rtl_f=str(f), kit_rtl_f_sha256=sha(f), n_src=len(srcs), n_kit=len(kit_files),
                  mismatch=bad, kit_only=extra, verdict='MATCH' if not bad else 'MISMATCH', files=rows)
    print(t, out[t]['verdict'], 'src', len(srcs), 'kit', len(kit_files), 'mismatch', bad, 'kit_only', extra)
Path(sys.argv[4]).write_text(json.dumps(out, indent=1) + '\n')
