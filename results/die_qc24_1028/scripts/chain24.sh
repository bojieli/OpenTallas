#!/bin/bash
# DIE-QC-24 trial24: stock trial14 tree on ev_qc23pg + --rep-off-leg-max 50 guard: kit -> bays -> overlay -> clock-only GRT TT/FF (docker 48g) -> snake/eval/validate -> gate24
set -u
D=/srv/opentallas-scratch2/claude/die-qc24-1028; MT=/srv/opentallas-scratch2/claude/wt/die-qc24-1028/tools/die_plan
cd $D
log(){ echo "$1 $(date)" >> $D/chain24.status; }
/usr/bin/time -v nice bash kit24.sh t24 > kit24.log 2>&1; log "kit rc $?"
grep -q "kit rc 0" <(tail -n1 chain24.status) && [ -s trial24/clock/tree.json ] && [ -s trial24/clock/ctree.v ] || { log "kit FAILED"; exit 1; }
python3 $MT/clock_body_bays.py $D/../die-qc23-1028/plan/ev_qc23pg.json $D/trial24/clock/tree.json --out $D/bays24 > bays24.log 2>&1; log "bays rc $?"
python3 overlay24.py > overlay24.log 2>&1; log "overlay rc $?"
bash run_clock24.sh TT > grt24_TT.log 2>&1 & bash run_clock24.sh FF > grt24_FF.log 2>&1 & wait; log "grt done $(grep -h EXIT c24_*/clock.log | tr "\n" " ")"
python3 /srv/opentallas-scratch2/claude/die-qc23-1028/scripts/snake_len23.py $MT $D/trial24 $D/c24_TT/arr_TT.txt /srv/opentallas-scratch2/claude/wt/die-qc24-1028/results/die_qc21_1028/inv2_stage_cal_trial13b.json snake_len24.json > snake24.log 2>&1; log "snake rc $?"
python3 -I /srv/opentallas-scratch2/claude/die-qc19-1028/eval13.py $D/trial24 $D/c24 $D/../die-qc23-1028/plan/ev_qc23pg.json $D/eval_trial24.json > eval24.log 2>&1; log "eval rc $?"
python3 /srv/opentallas-scratch2/claude/die-qc21-1028/validate.py $MT $D/trial24 $D/c24 $D/../die-qc23-1028/plan/ev_qc23pg.json /srv/opentallas-scratch2/claude/codex-die-qc-0359-1028/build_inputs/part_region.json $D/val24.json > val24.log 2>&1; log "val rc $?"
bash gate24.sh $D/trial24 $D/c24 g24; log "gate rc $?"
log DONE
