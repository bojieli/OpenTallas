#!/bin/bash
# DIE-QC-21 trial14: kit (stage-cal) -> bays -> overlay -> clock-only GRT TT/FF (docker 48g) -> eval -> gate21
set -u
D=/srv/opentallas-scratch2/claude/die-qc21-1028; MT=/srv/opentallas-scratch2/claude/wt/die-qc21-1028/tools/die_plan
cd $D
log(){ echo "$1 $(date)" >> $D/chain21.status; }
/usr/bin/time -v nice bash kit21.sh t13 > kit21.log 2>&1; log "kit rc $?"
grep -q "kit rc 0" <(tail -n1 chain21.status) && [ -s trial14/clock/tree.json ] && [ -s trial14/clock/ctree.v ] || { log "kit FAILED"; exit 1; }
python3 $MT/clock_body_bays.py /srv/opentallas-scratch2/claude/die-qc18-1028/gate/ev_a0meas.json $D/trial14/clock/tree.json --out $D/bays14 > bays14.log 2>&1; log "bays rc $?"
python3 overlay21.py > overlay21.log 2>&1; log "overlay rc $?"
bash run_clock21.sh TT > grt21_TT.log 2>&1 & bash run_clock21.sh FF > grt21_FF.log 2>&1 & wait; log "grt done $(grep -h EXIT c14_*/clock.log | tr "\n" " ")"
python3 -I /srv/opentallas-scratch2/claude/die-qc19-1028/eval13.py $D/trial14 $D/c14 /srv/opentallas-scratch2/claude/die-qc18-1028/gate/ev_a0meas.json $D/eval_trial14.json > eval21.log 2>&1; log "eval rc $?"
python3 validate.py /srv/opentallas-scratch2/claude/wt/die-qc21-1028/tools/die_plan $D/trial14 $D/c14 /srv/opentallas-scratch2/claude/die-qc18-1028/gate/ev_a0meas.json /srv/opentallas-scratch2/claude/codex-die-qc-0359-1028/build_inputs/part_region.json $D/val14.json > val14.log 2>&1; log "val rc $?"
bash gate21.sh $D/trial14 $D/c14 g14; log "gate rc $?"
log DONE
