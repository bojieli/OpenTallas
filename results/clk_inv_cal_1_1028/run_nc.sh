#!/bin/bash
# NUMBER-CHECK-CA-1 recompute (copy of ncca.py) on trial9: A row (reproduce), A pair-stages (reproduce), Ainv measured
M=/srv/opentallas-scratch2/claude/clk-inv-cal-1-1028; Q=/srv/opentallas-scratch2/claude/die-qc11-1028
CI=/srv/opentallas-scratch2/claude/codex-die-qc-0359-1028/build_inputs; PLAN=$CI/event/qc_k2b_phase12.json; MAP=$CI/part_region.json
TAB=/srv/opentallas-scratch2/claude/wt/clk-inv-cal-1/tools/die_plan/clk_aocv_table_g021.json
TR=${1:-t9}; N=${TR#t}; PO=${2:-$Q/ca/$TR/plan_phase.json}; TAG=${3:-old}
mkdir -p $M/nc; cd $M/nc
A="$Q/trial$N/clock/tree.json $Q/c${N}_TT/arr_TT.txt $Q/c${N}_FF/arr_FF.txt $PLAN $MAP $TAB $PO"
python3 -I $M/ncca_inv.py $A ${TR}_${TAG}_A.json --all > ${TR}_${TAG}_A.log 2>&1 &
python3 -I $M/ncca_inv.py $A ${TR}_${TAG}_Apair.json --all --inv-pair-stages > ${TR}_${TAG}_Apair.log 2>&1 &
python3 -I $M/ncca_inv.py $A ${TR}_${TAG}_Ainv.json --all --inv-cal > ${TR}_${TAG}_Ainv.log 2>&1 &
wait; tail -qn1 ${TR}_${TAG}_*.log
