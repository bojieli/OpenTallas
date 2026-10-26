#!/bin/bash
# H-D4G3b d4g GEN1: GEN0 plan/grants/regions + GEN1 netlist (d4g layers l1-l3 + 136-b lane relay layer on GEN0 pins),
# reset-reach gate FAIL mode, die repeaters at 405, regional clocks + neighbour-skew gate, lane rows placed as units.
set -o pipefail
R=$(cd "$(dirname "$0")" && pwd); cd $R/src
rm -rf $R/case $R/gen.log
D=results/arch/hbm_die_d4g
SM=wbk_SW=wbk_SW,wbk_NW=wbk_NW,sfup_SW=sfup_SW,sfup_SE=sfup_SE,sfup_NW=sfup_NW,sfup_NE=sfup_NE,refcfg_SW=refcfg_SW,refcfg_NW=refcfg_NW
OT_RESET_GATE=${OT_RESET_GATE:-fail} PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 MPLBACKEND=Agg /usr/bin/time -v python3 tools/hbm_die_v15/die_case_v16.py \
  --views $R/views --out $R/case --contract $R/views/contract.json --plan $D/plan/d4g_phy/compact.P.json --lanes $D/plan/d4g_phy/lanes.json \
  --grants $D/grants_d4g.json --compact-pins --max-pin-density 6 --die-repeaters --max-wire-um 405 --hold-budget die --paths 2000000 \
  --slot-map $SM --clock-mode hbm=regional,stream=regional,serial=regional --clock-region-map $D/d4g_region_map.json \
  --clock-near-um 405 --clock-region-max-um 4000 --diagnostic-param-alias > $R/gen.log 2>&1 || { echo GEN_FAIL; grep -v '^\s' $R/gen.log | tail -20; exit 3; }
echo GEN_OK; grep -E '^(clock|clock_check|clock_regions|reset_reach_gate|lane rows) ' $R/gen.log; grep -v '^\s' $R/gen.log | tail -4
python3 tools/hbm_die_v15/d4f_overreach.py $R/case $R/views/contract.json --out $R/overreach.json > $R/overreach.log 2>&1; echo OVERREACH rc=$?; head -5 $R/overreach.log
