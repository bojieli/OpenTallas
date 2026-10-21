#!/usr/bin/env python3
"""tok/s from a census schedule by the HBM-SUFIX delta rule: token = base token + (sched - base sched) / (1 + land%),
base = coll fork s0_base (DS 1004084.1 -> 1163.0 tok/s, land -1.13 %; Qwen 1195666.2 -> 1003.3, land -0.07 %); 1.2 GHz.
usage: tok_from_sched.py JOBDIR   (JOBDIR/info_banklat_all__{AR,qwen}.json)"""
import json, sys
from pathlib import Path
BASE = {'AR': (1004084.1, 1163.0, -1.13), 'qwen': (1195666.2, 1003.3, -0.07)}
res = {}
for k, (s0, t0, land) in BASE.items():
    s = json.loads((Path(sys.argv[1]) / f'info_banklat_all__{k}.json').read_text())['schedule_total']
    tok = 1.2e9 / t0 + (s - s0) / (1 + land / 100)
    res[k] = dict(schedule=s, token_cycles=round(tok, 1), tok_s=round(1.2e9 / tok, 1))
print(json.dumps(res))
