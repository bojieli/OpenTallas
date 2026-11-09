#!/bin/bash
# QC-TYPES-10/CLAND dry path on plan_qc53v4m_cland: validate, G0C completeness, count dry vs v4w (cmp_dry.py of QC-TYPES-9)
set -u
W=/srv/opentallas-scratch2/claude/qct10/cland; F=$W/farm; Q=/srv/opentallas-scratch2/claude/qct9; cd $F
PD=physical/die_plan/qwen_compute/plan_of_record; P=$PD/plan_qc53v4m_cland.json
mkdir -p $W/dry
python3 -B tools/die_plan/schema.py validate $P > $W/dry/validate.txt 2>&1; echo "VALIDATE rc $?" >> $W/dry/validate.txt
python3 -B tools/die_plan/check.py $P --completeness --out $W/dry/g0c_plan_qc53v4m_cland > $W/dry/check.txt 2>&1; echo "CHECK rc $?" >> $W/dry/check.txt
ln -sfn $Q/reach/dry/g0c_plan_qc53v4w $W/dry/g0c_plan_qc53v4w
python3 -B $Q/cmp_dry.py $Q/rtp $PD $W/dry plan_qc53v4w plan_qc53v4m_cland > $W/dry/compare.txt 2>&1; echo "CMP rc $?" >> $W/dry/compare.txt
