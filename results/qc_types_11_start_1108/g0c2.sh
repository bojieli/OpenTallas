#!/bin/bash
set -u
Q=/srv/opentallas-scratch3/claude/qct11/start; W=/srv/opentallas-scratch2/claude/qct11/wave; R=/srv/opentallas-scratch3/claude/codex-qc-compose-1113; S=$W/src
C=$S/physical/die_plan/qwen_compute/plan_of_record/census
for v in S n; do
  D=$Q/g0cp_$v; rm -rf $D; mkdir -p $D; ln -s $C $D/census; ln -s $W/plan/cores $D/cores
  if [ $v = S ]; then cp $W/plan/plan_qc53v4nS.json $D/p.json; else cp $R/plan/plan_qc53v4n.json $D/p.json; fi
  cd $S; python3 -B tools/die_plan/check.py $D/p.json --completeness --out $Q/dry/g0c2_$v > $Q/dry/c2_$v.txt 2>&1; echo "$v rc $?"
  grep -E "^G0C " $Q/dry/c2_$v.txt | cut -c1-240; tail -1 $Q/dry/c2_$v.txt | cut -c1-200
done
cd $S; for T in slw_fe_v2__clf110fab2 sle_stm_v3; do python3 -I -B tools/die_plan/kit_gen_lint.py $W/dry/$T/gen/$T --plan-dir $W/plan --no-yosys 2>&1 | tail -1 | cut -c1-240; done
echo G0C_END
