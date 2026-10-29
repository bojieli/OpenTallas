#!/bin/bash
# DIE-QC-25 trial25: stock trial14 tree on ev_qc25 + refit cal trial24 + --rep-on-leg + guard 50: kit -> bays -> overlay -> clock-only GRT TT/FF (docker 48g) -> snake/eval/validate -> gate25
set -u
D=/srv/opentallas-scratch2/claude/die-qc25-1028; MT=/srv/opentallas-scratch2/claude/wt/die-qc25-1028/tools/die_plan
cd $D
log(){ echo "$1 $(date)" >> $D/chain25.status; }
/usr/bin/time -v nice bash kit25.sh t25 > kit25.log 2>&1; log "kit rc $?"
grep -q "kit rc 0" <(tail -n1 chain25.status) && [ -s trial25/clock/tree.json ] && [ -s trial25/clock/ctree.v ] || { log "kit FAILED"; exit 1; }
python3 $MT/clock_body_bays.py $D/plan/ev_qc25.json $D/trial25/clock/tree.json --out $D/bays25 > bays25.log 2>&1; log "bays rc $?"
python3 overlay25.py > overlay25.log 2>&1; log "overlay rc $?"
bash run_clock25.sh TT > grt25_TT.log 2>&1 & bash run_clock25.sh FF > grt25_FF.log 2>&1 & wait; log "grt done $(grep -h EXIT c25_*/clock.log | tr "\n" " ")"
python3 /srv/opentallas-scratch2/claude/die-qc23-1028/scripts/snake_len23.py $MT $D/trial25 $D/c25_TT/arr_TT.txt /srv/opentallas-scratch2/claude/wt/die-qc25-1028/results/die_qc25_1028/inv2_stage_cal_trial24.json snake_len25.json > snake25.log 2>&1; log "snake rc $?"
python3 -I /srv/opentallas-scratch2/claude/die-qc19-1028/eval13.py $D/trial25 $D/c25 $D/plan/ev_qc25.json $D/eval_trial25.json > eval25.log 2>&1; log "eval rc $?"
python3 /srv/opentallas-scratch2/claude/die-qc21-1028/validate.py $MT $D/trial25 $D/c25 $D/plan/ev_qc25.json /srv/opentallas-scratch2/claude/codex-die-qc-0359-1028/build_inputs/part_region.json $D/val25.json > val25.log 2>&1; log "val rc $?"
bash gate25.sh $D/trial25 $D/c25 g25; log "gate rc $?"
log DONE
