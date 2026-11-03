#!/bin/bash
# DIE-QC-66/CLK: recompute the RE-FORM die clock estimate (light, JSON only). Args: tree.json die_sta_related.json label
W=$(git rev-parse --show-toplevel); R=$W/results/qc_die66_clk_1103
python3 $R/qc_reform_clk_estimate.py --plan $W/physical/die_plan/qwen_compute/plan_of_record/plan_qc52.json \
  --cells $W/physical/die_plan/qwen_compute/plan_of_record/cells/qc_cells_evidence_1102.json --repo $W \
  --char $R/char_flop_latch.json --tree "$1" --sta "$3=$2" --out $R
