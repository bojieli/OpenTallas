#!/bin/bash
set -u
Q=/srv/opentallas-scratch3/claude/qct11/start; R=/srv/opentallas-scratch3/claude/codex-qc-compose-1113; S=$R/src_fixed
mkdir -p $Q/dry; cd $S
python3 -B tools/die_plan/check.py $Q/plan/plan_qc53v4nS.json --completeness --out $Q/dry/g0c_S > $Q/dry/check_S.txt 2>&1; echo "CHECK_S rc $?"
python3 -B tools/die_plan/check.py $R/plan/plan_qc53v4n.json --completeness --out $Q/dry/g0c_n > $Q/dry/check_n.txt 2>&1; echo "CHECK_n rc $?"
tail -2 $Q/dry/check_S.txt | cut -c1-260; tail -2 $Q/dry/check_n.txt | cut -c1-260
ls $Q/dry/g0c_S $Q/dry/g0c_n | head
