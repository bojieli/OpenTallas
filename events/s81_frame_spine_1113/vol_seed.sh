#!/bin/bash
W=/srv/opentallas-scratch3/claude/wt/frame-forms-1; F=/srv/opentallas-scratch3/claude/frame-forms-1; E=$W/events/s81_frame_spine_1113; A=/srv/opentallas-scratch3/claude/frame-forms-1/all1; cd $A
python3 -I $E/frame_spine_seed.py $F/w/plan_A.json seed_all.json --conns $W/physical/die_plan/s81/core_conns.json --report seed_rep.json > seed.log 2>&1; echo SEED_RC=$?
python3 -I $E/park_taps.py $F/w/plan_A.json seed_all.json plan_A_tp.json > park.log 2>&1; echo PARK_RC=$?; cat park.log
