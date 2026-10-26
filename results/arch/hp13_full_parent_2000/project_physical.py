#!/usr/bin/env python3
"""Regenerate the HP13 cpub39 synthesis projections per SYNTHESIS_PROJECTION.json.

Rule (unchanged from Codex 4a71f1238/9679b8f30): remove only the two ROM image metadata
annotations `#(.INSTANCE("calendar_m0")) ` and `#(.INSTANCE("calendar_m1")) `; every other byte
equal. Each token must occur exactly once. Rewrites SYNTHESIS_PROJECTION.json sha256s.
Run from the repository root.
"""
import hashlib, json, re
from pathlib import Path

root = Path(__file__).resolve().parents[3]
recp = root / 'results/arch/hp13_full_parent_2000/SYNTHESIS_PROJECTION.json'
rec = json.loads(recp.read_text())
sha = lambda b: hashlib.sha256(b).hexdigest()
for r in rec:
    src = (root / r['original']).read_bytes()
    out = src
    for tok in r['only_removed']:
        t = tok.encode()
        assert out.count(t) == 1, (r['original'], tok, out.count(t))
        out = out.replace(t, b'')
    # remaining-bytes check: re-insert at the removal points reproduces the source exactly
    assert len(src) - len(out) == sum(len(t.encode()) for t in r['only_removed'])
    assert b'INSTANCE' not in out and b'VIAMAP' not in out
    (root / r['projection']).write_bytes(out)
    r['original_sha256'] = sha(src)
    r['projection_sha256'] = sha(out)
    r['remaining_bytes_equal'] = True
    print(r['original'], r['original_sha256'][:8], '->', r['projection'], r['projection_sha256'][:8])
recp.write_text(json.dumps(rec, indent=2) + '\n')
