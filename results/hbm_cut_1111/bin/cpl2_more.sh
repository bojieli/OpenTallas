#!/bin/bash
set -u
W=/srv/opentallas-scratch2/claude/hbm-cut-1111; cd /
mkdir -p $W/inputs/cpl2/full
for t in q_su21 q_su21__physical_v1 q_spb2 q_spb2__physical_v1; do
  timeout 600 scp -q epyc4:/srv/opentallas-scratch3/claude/cpl-hbm-2-run/pure/cc_taps/plan_$t.json $W/inputs/cpl2/full/ || echo "SCP_FAIL $t"
done
sha256sum $W/inputs/cpl2/full/*
for t in q_su21 q_su21__physical_v1 q_spb2 q_spb2__physical_v1; do
  python3 -I $W/bin/typedelta.py $W/base $W/inputs/cpl2/full/plan_$t.json adopt_cpl2_$t $W/deltas/d4_adopt_cpl2_$t.json $t
done
echo CPL2_MORE_DONE
