#!/bin/bash
# combined what-if: faster upper tree (16w L1-9, 3x BUFx24) rec + graded split-line band, 24 samples, TT+FF
cd /srv/opentallas-scratch2/claude/path-s81-pd12-1027; export PYTHONPATH=/srv/opentallas-scratch2/claude/clock-kv-r18-1027/in/pylib; ulimit -v 32000000
for cfg in 128,6000,prop 128,4000,prop; do IFS=, read W B K <<< "$cfg"; for C in TT FF; do N=x3g${W}_${B}_${K}_$C
 python3 pd13/whatif_grade.py pd13/wf/16w_L1-9_x3_$C.json.rec.json $W $B $K $C 24 pd13/wc/$N.json me1v/mesh_$C.json /srv/opentallas-scratch2/claude/wt/main-tools-pd13/tools/die_plan/kv_r7 /srv/opentallas-scratch2/claude/wt/main-tools-pd13/tools/die_plan/kv_r18/mesh_mc18.py /srv/opentallas-scratch2/claude/clock-kv-r17-1027/thev_qc_m2.json > pd13/wc/$N.log 2>&1 &
done; done; wait; echo WC_DONE $(date -Is)
