#!/bin/bash
set -u
W=/srv/opentallas-scratch2/claude/hbm-cut-1111; D=$W/deltas; cd /
mv $D/d4c_adopt_cpl2fin_q_spb2.json $D/d4c_adopt_cpl2fin_q_spt0.json $D/d4c_adopt_cpl2fin_q_spt0__physical_v1.json $D/withdrawn/
mv $D/withdrawn/d4_adopt_cpl2_q_spb2_5cf24058.json $D/d4_adopt_cpl2_q_spb2.json
sha256sum $W/inputs/cpl2/full/plan_q_spb2.json
mkdir -p $W/inputs/cpl2/lift2
for t in q_spt0 q_spt0__physical_v1; do timeout 600 scp -q epyc4:/srv/opentallas-scratch3/claude/cpl-hbm-2-run/lift2/cc_taps/plan_$t.json $W/inputs/cpl2/lift2/ || echo SCP_FAIL $t; done
sha256sum $W/inputs/cpl2/lift2/*
for t in q_spt0 q_spt0__physical_v1; do python3 -I $W/bin/typedelta.py $W/base $W/inputs/cpl2/lift2/plan_$t.json adopt_cpl2lift_$t $D/d4_adopt_cpl2lift_$t.json $t; done
ls $D; echo LIFT_DONE
