#!/bin/bash
# L2H-IDXSEL 10-19: drain-margin probe for mut_drain (survived at shift 1). Shift each scan pass's op5 block k edges
# earlier into the drain slots (k=1..3 when the k slots before it are op0 drain slots of the same pass) and run the
# already-built full-shape bench binary (bench/sched2/obj).
set -uo pipefail
B=/srv/opentallas-scratch/claude/l2h-idxsel/bench/sched2
P=/srv/opentallas-scratch/claude/l2h-idxsel/bench/drainprobe
mkdir -p $P
read -r ek et <<< "$(python3 -c 'import json,sys;p=json.load(open(sys.argv[1]))["predicted"];print(p["first_key_instruction"]+3,p["first_tx_from_instruction0"]+3)' $B/cal_reg100/calendar.json)"
N=$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["length"])' $B/cal_reg100/calendar.json)
for k in 1 2 3 4; do
 python3 - $B/cal_reg100 $P/cal_d$k $k <<'PY' || { echo "SHIFT $k: no room (drain slots)"; continue; }
import pathlib, sys
src, dst, k = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2]), int(sys.argv[3]); dst.mkdir(parents=True, exist_ok=True)
words = [int(x, 16) for x in (src / 'calendar_instructions.hex').read_text().split()]
SEL = (15 << 16) | (3 << 14) | (255 << 6)
for ps in (1, 2):
    idx = [i for i, w in enumerate(words) if ((w >> 16) & 15) == 5 and ((w >> 14) & 3) == ps]
    assert idx == list(range(idx[0], idx[0] + len(idx))), ps
    for j in range(1, k + 1):
        pre = words[idx[0] - j]
        if not (((pre >> 16) & 15) == 0 and ((pre >> 14) & 3) == ps): sys.exit(f'slot -{j} before op5 pass {ps} is {pre:08x}')
    vals = [words[i] & SEL for i in idx]
    for n, i in enumerate(idx): words[i - k] = (words[i - k] & ~SEL) | vals[n]
    for i in idx[-k:]: words[i] = (words[i] & ~SEL) | (ps << 14)
(dst / 'calendar_instructions.hex').write_text(''.join(f'{w:08x}\n' for w in words))
(dst / 'calendar.json').write_text((src / 'calendar.json').read_text())
print('shift', k, 'ok')
PY
 r=$P/run_d$k; mkdir -p $r; cp $B/vec/*.hex $r/; cp $P/cal_d$k/calendar_instructions.hex $r/
 (cd $r && $B/obj/Vtb_idx_scheduled_static +N=$N +MUT=0 +EXP_KEY=$ek +EXP_TX=$et) > $P/run_d$k.log 2>&1; rc=$?
 echo "SHIFT $k rc=$rc"; grep -E "IDX_SCHEDULED_STATIC|SCOREBAD|TXBAD|TIMELINE" $P/run_d$k.log | head -6 | sed "s/^/[d$k] /"
done
