#!/bin/bash
cd /srv/opentallas-scratch2/claude/vislayout2-qc/sc
run() { v=$1; shift; nice -n 19 python3 -I -B make_sc2.py ../src25 ../planq25/plan_qc99_s25.json plan/plan_sc_$v.json plan/ledger_$v.json "$@" > plan/make_$v.log 2>&1 && cp plan/plan_sc_$v.json ../planq25/ && bash score.sh plan_sc_$v > score_$v.out 2>&1; }
run l --ewjog 467.64 --band x_ctl_su_c_p2=284.0,343.0 --x 237.6 --ytop 1188.0 --nsjog x_ctl_su_c=604.8 --nsjog x_ctl_su_c_p1=561.6 &
run m --ewjog 467.64 --band x_ctl_su_c_p2=284.0,343.0 --x 237.6 --ytop 1175.04 --nsjog x_ctl_su_c=604.8 --nsjog x_ctl_su_c_p1=561.6 &
wait; echo LMDONE
