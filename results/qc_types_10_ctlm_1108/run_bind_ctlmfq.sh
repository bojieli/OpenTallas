#!/bin/bash
# QC-TYPES-10/CTLM 11-08: elab + strict native bind of plan_qc53v4w_ctlmfq from the private FQREG src overlay
set -u
D=/srv/opentallas-scratch2/claude/qct10/ctlm; S=$D/src_ctlmfq; P=$D/plan/plan_qc53v4w_ctlmfq.json; O=$D/bind_ctlmfq
A=$S/physical/die_plan/qwen_compute/qc_start_1106/runtime/asbuilt_reach.json
cd $S; mkdir -p $O; date
python3 -B tools/die_plan/schema.py validate $P > $D/validate.txt 2>&1; echo "VALIDATE rc $?" >> $D/validate.txt; tail -2 $D/validate.txt
python3 -B tools/die_plan/bind.py elab $P --out $O --asbuilt $A > $D/elab.log 2>&1; echo "ELAB rc $?" >> $D/elab.log; tail -2 $D/elab.log; date
python3 -B tools/die_plan/bind.py bind $P --out $O --strict --asbuilt $A > $D/bind.log 2>&1; echo "BIND rc $?" >> $D/bind.log; tail -4 $D/bind.log; date
