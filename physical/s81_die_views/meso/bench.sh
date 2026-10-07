#!/bin/bash
# CLAUDE S81-RERUN: ot_meso_fifo W512 D4 transaction bench for the closure loop (tools/meso_fifo_campaign.py's bench,
# rtl/test/meso/tb_meso_fifo.cpp, Verilator).  usage: bench.sh <pass|mut> <work dir>
#   pass: d4_central (DEPTH 4 / OFFSET 2 / guards 0,4 / CREDITS 8), 8+5 static phases x {random, stream, bp, reset} at
#         +-192 ps wander, 200k cycles each: every word delivered in order, 0 errors, 0 false faults
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
cfg = C.CONFIGS['d4_central']
tb = C.build(W, 'mut_OFFSET' if mode == 'mut' else 'd4', cfg, 'OT_MESO_MUTANT_OFFSET' if mode == 'mut' else '')
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
