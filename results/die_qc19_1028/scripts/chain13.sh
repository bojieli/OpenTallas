#!/bin/bash
# DIE-QC-19 trial13: bays -> overlay -> clock-only GRT TT/FF (docker 48g probe, as QC-16 trial12) -> eval -> gate
set -u
D=/srv/opentallas-scratch2/claude/die-qc19-1028; MT=/srv/opentallas-scratch2/claude/wt/die-qc19-1028/tools/die_plan
cd $D
log(){ echo "$1 $(date)" >> $D/chain13.status; }
python3 $MT/clock_body_bays.py /srv/opentallas-scratch2/claude/die-qc18-1028/gate/ev_a0meas.json $D/trial13/clock/tree.json --out $D/bays13 > bays13.log 2>&1; log "bays rc $?"
python3 overlay13.py > overlay13.log 2>&1; log "overlay rc $?"
bash run_clock13.sh TT > grt13_TT.log 2>&1 & bash run_clock13.sh FF > grt13_FF.log 2>&1 & wait; log "grt done $(grep -h EXIT c13_*/clock.log | tr "\n" " ")"
python3 -I eval13.py $D/trial13 $D/c13 /srv/opentallas-scratch2/claude/die-qc18-1028/gate/ev_a0meas.json $D/eval_trial13.json > eval13.log 2>&1; log "eval rc $?"
bash gate13.sh trial13 c13 g13; log "gate rc $?"
log DONE
