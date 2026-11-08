#!/bin/bash
# QC-TYPES-10/FWS 11-08: plan_qc53v4x_fws dry path (validate, G0C, count dry vs v4w, elab + strict native bind)
set -u
Q=/srv/opentallas-scratch2/claude/qct9; W=/srv/opentallas-scratch3/claude/qct10/fws; F=$W/farm; cd $F
PD=physical/die_plan/qwen_compute/plan_of_record; P=$PD/plan_qc53v4x_fws.json
A=physical/die_plan/qwen_compute/qc_start_1106/runtime/asbuilt_reach.json
mkdir -p $W/dry
cp $W/plan_qc53v4x_fws.json $P; cmp $W/plan_qc53v4w.json $PD/plan_qc53v4w.json && echo "v4w base identical"
date
python3 -B tools/die_plan/schema.py validate $P > $W/dry/validate.txt 2>&1; echo "VALIDATE rc $?" >> $W/dry/validate.txt
python3 -B tools/die_plan/check.py $P --completeness --out $W/dry/g0c_plan_qc53v4x_fws > $W/dry/check.txt 2>&1; echo "CHECK rc $?" >> $W/dry/check.txt
ln -sfn $W/aux/g0c_plan_qc53v4w $W/dry/g0c_plan_qc53v4w
python3 -B $W/aux/cmp_dry.py $W/aux/rtp $PD $W/dry plan_qc53v4w plan_qc53v4x_fws > $W/dry/compare.txt 2>&1; echo "CMP rc $?" >> $W/dry/compare.txt
date
python3 -B tools/die_plan/bind.py elab $P --out $W/bind_v4x --asbuilt $A > $W/elab.log 2>&1; echo "ELAB rc $?" >> $W/elab.log
date
python3 -B tools/die_plan/bind.py bind $P --out $W/bind_v4x --strict --asbuilt $A > $W/bind.log 2>&1; echo "BIND rc $?" >> $W/bind.log
date
