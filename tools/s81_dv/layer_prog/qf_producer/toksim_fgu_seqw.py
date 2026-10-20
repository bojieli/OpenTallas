#!/usr/bin/env python3
"""TOKSIM-S81B/FGU (10-19): write <seq_dir>/seqw.hex = per phase of seq.json the number of frame RET words its compiled
return calendar predicts (len(meta.plan.ret) of the phase vector), for tb_toksim_fgu_seq +RETIRE=1.
    toksim_fgu_seqw.py VEC seq_experts_gu [seq_shared_gu ...]"""
import json
import sys
from pathlib import Path

vec = Path(sys.argv[1])
for sn in sys.argv[2:]:
    sq = json.loads((vec / sn / 'seq.json').read_text())
    w = [len(json.loads((vec / v / 'meta.json').read_text())['plan']['ret']) for v in sq['vectors']]
    (vec / sn / 'seqw.hex').write_text(''.join(f'{x:04x}\n' for x in w))
    print('TOKSIM_FGU_SEQW', sn, w)
