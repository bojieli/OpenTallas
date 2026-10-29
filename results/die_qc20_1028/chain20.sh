#!/bin/bash
# DIE-QC-20 trial13b: kit (join budget) -> bays -> overlay -> clock-only GRT TT/FF (docker 48g) -> eval -> gate20 (main tools, RM165)
set -u
D=/srv/opentallas-scratch2/claude/die-qc20-1028; MT=/srv/opentallas-scratch2/claude/wt/die-qc20-1028/tools/die_plan
cd $D
log(){ echo "$1 $(date)" >> $D/chain20.status; }
/usr/bin/time -v nice bash kit20.sh t13 > kit20.log 2>&1; log "kit rc $?"
grep -q "kit rc 0" <(tail -n1 chain20.status) && [ -s trial13b/clock/tree.json ] && [ -s trial13b/clock/ctree.v ] || { log "kit FAILED"; exit 1; }
python3 $MT/clock_body_bays.py /srv/opentallas-scratch2/claude/die-qc18-1028/gate/ev_a0meas.json $D/trial13b/clock/tree.json --out $D/bays13 > bays13.log 2>&1; log "bays rc $?"
python3 overlay20.py > overlay20.log 2>&1; log "overlay rc $?"
bash run_clock20.sh TT > grt20_TT.log 2>&1 & bash run_clock20.sh FF > grt20_FF.log 2>&1 & wait; log "grt done $(grep -h EXIT c13b_*/clock.log | tr "\n" " ")"
python3 -I /srv/opentallas-scratch2/claude/die-qc19-1028/eval13.py $D/trial13b $D/c13b /srv/opentallas-scratch2/claude/die-qc18-1028/gate/ev_a0meas.json $D/eval_trial13b.json > eval20.log 2>&1; log "eval rc $?"
bash gate20.sh $D/trial13b $D/c13b g13b; log "gate rc $?"
log DONE
