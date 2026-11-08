#!/bin/bash
# QC-TYPES-10/FWS: elab + strict native bind of plan_qc53v4x_fws (asbuilt_reach.json + r8_reach.json of v4w, private runtime copy)
set -u
W=/srv/opentallas-scratch3/claude/qct10/fws; cd $W/farm
P=physical/die_plan/qwen_compute/plan_of_record/plan_qc53v4x_fws.json; A=physical/die_plan/qwen_compute/qc_start_1106/runtime/asbuilt_reach.json
date
python3 -B tools/die_plan/bind.py elab $P --out $W/bind_v4x --asbuilt $A > $W/elab.log 2>&1; echo "ELAB rc $?" >> $W/elab.log
date
python3 -B tools/die_plan/bind.py bind $P --out $W/bind_v4x --strict --asbuilt $A > $W/bind.log 2>&1; echo "BIND rc $?" >> $W/bind.log
date
