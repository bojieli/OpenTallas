#!/bin/bash
# CLAUDE S81-RERUN: ot_meso_fifo W512 D4 transaction bench for the closure loop (tools/meso_fifo_campaign.py's bench,
# rtl/test/meso/tb_meso_fifo.cpp, Verilator).  usage: bench.sh <pass|mut> <work dir>
#   pass: d8g1 (DEPTH 8 / OFFSET 4 / guards 1,7 / CREDITS 16), 8+5 static phases x {random, stream, bp, reset} at
#         +-386 ps wander (the S81 stream-trunk drift), 200k cycles each: every word delivered in order, 0 errors, 0 false faults
#   mut : the same bench on the OT_MESO_MUTANT_OFFSET build (placement window off by one): must be caught
set -u
mode=$1; W=$2; mkdir -p $W
cd "$(dirname "$0")/../../.."
python3 - "$mode" "$W" <<'PY'
import sys, json, math
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, 'tools')
import meso_fifo_campaign as C
mode, W = sys.argv[1], Path(sys.argv[2])
cfg = dict(depth=8, offset=4, glo=1, ghi=7, credits=16, wander=386.0)   # d8g1: the S81 die meso (crossing arcs 1.5 T)
tb = C.build(W, 'mut_OFFSET' if mode == 'mut' else 'd8g1', cfg,
             'OT_MESO_PINREG -DOT_MESO_MUTANT_OFFSET' if mode == 'mut' else 'OT_MESO_PINREG')   # PINREG = the view's RTL
jobs = []
for i, ph in enumerate(C.phases(8)):
    for m in ('random', 'stream', 'bp', 'reset'):
        jobs.append(dict(mode=m, phase=ph, wander=cfg['wander'], wph=round(math.pi / 2 * (1 if i % 2 else -1), 6),
                         wperiod=20000, cycles=200000, seed=11 + i, credits=cfg['credits']))
with ThreadPoolExecutor(4) as ex:
    recs = list(ex.map(lambda j: C.run(tb, **j), jobs))
bad = [r for r in recs if r['rc'] != 0 or r.get('errors', -1) != 0]
(W / f'bench_{mode}.json').write_text(json.dumps(recs))
print(f'MESO_BENCH {"PASS" if not bad else "FAIL"} {len(recs) - len(bad)}/{len(recs)} runs clean'
      + (f'; first failure {bad[0]["args"]} {bad[0]["error_lines"][:1]}' if bad else ''))
sys.exit(1 if bad else 0)
PY
