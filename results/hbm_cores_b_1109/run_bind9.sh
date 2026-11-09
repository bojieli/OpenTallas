#!/bin/bash
# QC-MEM9-RTL: strict native bind proof of the EXTRA9 event on plan v4w_ctlmfq (private overlay)
set -u
D=/srv/opentallas-scratch2/claude/qc-mem9-rtl/bind9; S=$D/src; P=$D/plan_qc53v4w_mem9.json; O=$D/bind_out
A=$S/physical/die_plan/qwen_compute/qc_start_1106/runtime/asbuilt_reach.json
cd $S; mkdir -p $O; date
python3 -B tools/die_plan/schema.py validate $P > $D/validate.txt 2>&1; echo "VALIDATE rc $?" >> $D/validate.txt; tail -2 $D/validate.txt
python3 -B tools/die_plan/bind.py elab $P --out $O --asbuilt $A > $D/elab.log 2>&1; echo "ELAB rc $?" >> $D/elab.log; tail -2 $D/elab.log; date
python3 -B tools/die_plan/bind.py bind $P --out $O --strict --asbuilt $A > $D/bind.log 2>&1; echo "BIND rc $?" >> $D/bind.log; tail -4 $D/bind.log; date
echo BIND9-DONE
