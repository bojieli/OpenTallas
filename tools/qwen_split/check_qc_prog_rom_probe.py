#!/usr/bin/env python3
"""DIE-QC-59P probe checker: model read-back == generator logical words (sys_face_cfg) and == viamap decode (others)."""
import sys, json
from pathlib import Path
d = Path(sys.argv[1]); words = Path(sys.argv[2]); logical = Path(sys.argv[3])
def decode(p, bits):
    rows = [int(l, 16) for l in Path(p).read_text().split()]
    assert 0 < len(rows) <= 512, p
    rows += [0] * (512 - len(rows))
    return [sum(((rows[a // 8] >> (b * 8 + a % 8)) & 1) << b for b in range(bits)) for a in range(4096)]
exp_sf = [int(l, 16) for l in logical.read_text().split()]
exp = dict(sf=exp_sf, c0=decode(d / 'calendar_m0.viamap.hex', 266),
           c1=decode(d / 'calendar_m1.viamap.hex', 266), t0=decode(d / 'table_s0_m0.viamap.hex', 266))
bad = {k: 0 for k in exp}; nz = {k: 0 for k in exp}; n = 0
for line in words.read_text().split('\n'):
    if not line.strip(): continue
    f = line.split(); a = int(f[0]); n += 1
    for k, v in zip(('sf', 'c0', 'c1', 't0'), f[1:]):
        got = int(v, 16)
        nz[k] += got != 0
        if got != exp[k][a]: bad[k] += 1
print(json.dumps(dict(words=n, mismatches=bad, nonzero_words=nz)))
sys.exit(0 if n == 4096 and not any(bad.values()) else 1)
