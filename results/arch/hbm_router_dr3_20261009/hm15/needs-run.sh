#!/bin/bash
set -u
D=/srv/opentallas-scratch/codex/hbm-router-dr3-needs-e384a2d2c
R=/srv/opentallas-scratch/claude/closure-loop/hbm_router_kneg_orph2_a75cb556b-ttref-hm15
O=$R/routes/hbm_router_kneg_orph2_a75cb556b_ttref_hm15/work/orfs
/srv/opentallas-scratch/admit.sh 23 -- /usr/bin/time -v python3 "$D/meas_resta.py" --orfs "$O" --src "$R/src" --out "$D/needs.json" --append "$R/cl/io_ref_routed.sdc" --append "$D/rebudget_measure.sdc" > "$D/needs.log" 2>&1
echo $? > "$D/exit.rc"
