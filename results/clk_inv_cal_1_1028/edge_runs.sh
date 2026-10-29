#!/bin/bash
# CLK-INV-CAL-2: intra/landed die STA, spice vs spice_edge, S81 go13 + QC t10 (declared inv), no CA bind
set -u
M=/srv/opentallas-scratch2/claude/clk-inv-cal-1-1028; MT=/srv/opentallas-scratch2/claude/wt/clk-inv-cal-1/tools/die_plan
S=/srv/opentallas-scratch2/claude/die-s81-13; PLS=/srv/opentallas-scratch2/claude/die-s81-10/plan/plan_s10.json
CI=/srv/opentallas-scratch2/claude/codex-die-qc-0359-1028/build_inputs; PLQ=$CI/event/qc_k2b_phase12.json; Q=$M/qc/t10/proof_fall
mkdir -p $M/edge
run(){ # tag proof plan cal
  python3 $MT/die_sta_related.py $2 --plan $3 --out $M/edge/$1 --corner TT --corner FF --clock-ocv table --clock-droop shared --droop-regions $2/droop_regions.json --core-latency-ff 202.5 --hold-buffers none --cppr-lca --clock-cal $4 --clock-cell inv > $M/edge/$1.log 2>&1; echo "$1 rc $? $(date)" >> $M/edge/runs.log; }
run s81_spice $S/proof $PLS spice & run s81_edge $S/proof $PLS spice_edge & run qc_spice $Q $PLQ spice & run qc_edge $Q $PLQ spice_edge & wait
echo ALLDONE >> $M/edge/runs.log
