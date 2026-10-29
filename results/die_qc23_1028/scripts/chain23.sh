#!/bin/bash
# DIE-QC-23 trial15: kit (plan ev_qc23 + --region-dme-snake-cap 1200) -> bays -> overlay -> clock-only GRT TT/FF (docker 48g) -> snake/eval/validate -> gate23
set -u
D=/srv/opentallas-scratch2/claude/die-qc23-1028; MT=/srv/opentallas-scratch2/claude/wt/die-qc22-1028/tools/die_plan
cd $D
log(){ echo "$1 $(date)" >> $D/chain23.status; }
/usr/bin/time -v nice bash kit23.sh t15 > kit23.log 2>&1; log "kit rc $?"
grep -q "kit rc 0" <(tail -n1 chain23.status) && [ -s trial15/clock/tree.json ] && [ -s trial15/clock/ctree.v ] || { log "kit FAILED"; exit 1; }
python3 $MT/clock_body_bays.py $D/plan/ev_qc23.json $D/trial15/clock/tree.json --out $D/bays15 > bays15.log 2>&1; log "bays rc $?"
python3 overlay23.py > overlay23.log 2>&1; log "overlay rc $?"
bash run_clock23.sh TT > grt23_TT.log 2>&1 & bash run_clock23.sh FF > grt23_FF.log 2>&1 & wait; log "grt done $(grep -h EXIT c15_*/clock.log | tr "\n" " ")"
python3 scripts/snake_len23.py $MT $D/trial15 $D/c15_TT/arr_TT.txt /srv/opentallas-scratch2/claude/wt/die-qc22-1028/results/die_qc21_1028/inv2_stage_cal_trial13b.json snake_len15.json > snake15.log 2>&1; log "snake rc $?"
python3 -I /srv/opentallas-scratch2/claude/die-qc19-1028/eval13.py $D/trial15 $D/c15 $D/plan/ev_qc23.json $D/eval_trial15.json > eval23.log 2>&1; log "eval rc $?"
python3 /srv/opentallas-scratch2/claude/die-qc21-1028/validate.py $MT $D/trial15 $D/c15 $D/plan/ev_qc23.json /srv/opentallas-scratch2/claude/codex-die-qc-0359-1028/build_inputs/part_region.json $D/val15.json > val15.log 2>&1; log "val rc $?"
bash gate23.sh $D/trial15 $D/c15 g15; log "gate rc $?"
log DONE
