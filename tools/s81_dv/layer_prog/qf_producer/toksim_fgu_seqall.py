#!/usr/bin/env python3
"""TOKSIM-S81B/FGU (10-19): seq_gu_all = shared_gu then experts_gu phases (field order 16..43) of the frame back to back.
The two seq dirs carry byte-identical field images (one compile_frame), so the union is a copy of seq_experts_gu with
the concatenated seq.hex / seqw.hex / seq.json.    toksim_fgu_seqall.py VEC"""
import json
import shutil
import sys
from pathlib import Path

vec = Path(sys.argv[1])
a, b = vec / 'seq_shared_gu', vec / 'seq_experts_gu'
d = vec / 'seq_gu_all'
if d.exists():
    shutil.rmtree(d)
shutil.copytree(b, d)
sa, sb = (json.loads((x / 'seq.json').read_text()) for x in (a, b))
assert max(sa['phases']) < min(sb['phases'])
for f in ('seq.hex', 'seqw.hex'):
    (d / f).write_text((a / f).read_text() + (b / f).read_text())
(d / 'seq.json').write_text(json.dumps(dict(op='ffn.shared_gu+ffn.experts_gu', frame=sa['frame'],
                                            phases=sa['phases'] + sb['phases'], rows=sa['rows'] + sb['rows'], K=sa['K'],
                                            vectors=sa['vectors'] + sb['vectors']), indent=1) + '\n')
print('TOKSIM_FGU_SEQALL', len(sa['phases']) + len(sb['phases']))
