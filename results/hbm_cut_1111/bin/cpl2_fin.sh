#!/bin/bash
set -u
W=/srv/opentallas-scratch2/claude/hbm-cut-1111; D=$W/deltas; cd /
mkdir -p $W/inputs/cpl2/fin
for t in q_spb2 q_spt0 q_spt0__physical_v1; do timeout 600 scp -q epyc4:/srv/opentallas-scratch3/claude/cpl-hbm-2-run/fin/cc_taps/plan_$t.json $W/inputs/cpl2/fin/ || echo SCP_FAIL $t; done
sha256sum $W/inputs/cpl2/fin/*
mv $D/d4_adopt_cpl2_q_spb2.json $D/withdrawn/d4_adopt_cpl2_q_spb2_5cf24058.json; mv $D/d4_adopt_cpl2_q_spb2__physical_v1.json $D/withdrawn/
for t in q_spb2 q_spt0 q_spt0__physical_v1; do python3 -I $W/bin/typedelta.py $W/base $W/inputs/cpl2/fin/plan_$t.json adopt_cpl2fin_$t $D/d4c_adopt_cpl2fin_$t.json $t; done
echo FIN_DONE
