#!/bin/bash
# H-D4G d4g GEN0 (DIAGNOSTIC: d4f r8b netlist, LAYER=none, on the d4g plan/grants; the RTL lanes HBM-B-RTL1..3 not landed)
# plan d4g_phy, grants_d4g (slots follow their plan block), regional clocks per quadrant (d4g_region_map) + neighbour-skew gate,
# die repeaters at 405, reset reachability gate in diag (no reset forest layer yet), relay-free (lanes planned from these pins).
set -o pipefail
R=$(cd "$(dirname "$0")" && pwd); cd $R/src
rm -rf $R/case $R/gen.log
D=results/arch/hbm_die_d4g
SM=wbk_SW=wbk_SW,wbk_NW=wbk_NW,sfup_SW=sfup_SW,sfup_SE=sfup_SE,sfup_NW=sfup_NW,sfup_NE=sfup_NE,refcfg_SW=refcfg_SW,refcfg_NW=refcfg_NW
OT_RESET_GATE=diag PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 MPLBACKEND=Agg /usr/bin/time -v python3 tools/hbm_die_v15/die_case_v16.py \
  --views $R/views --out $R/case --contract $R/views/contract.json --plan $D/plan/d4g_phy/compact.P.json --lanes $D/plan/d4g_phy/lanes.json \
  --grants $D/grants_d4g.json --compact-pins --max-pin-density 6 --die-repeaters --max-wire-um 405 --hold-budget die --paths 2000000 \
  --slot-map $SM --clock-mode hbm=regional,stream=regional,serial=regional --clock-region-map $D/d4g_region_map.json \
  --clock-near-um 405 --clock-region-max-um 4000 --diagnostic-param-alias > $R/gen.log 2>&1 || { echo GEN_FAIL; grep -v '^\s' $R/gen.log | tail -20; exit 3; }
echo GEN_OK; grep -E '^(clock|clock_check|clock_regions|reset_reach_gate) ' $R/gen.log; grep -v '^\s' $R/gen.log | tail -4
python3 tools/hbm_die_v15/d4f_overreach.py $R/case $R/views/contract.json --out $R/overreach.json > $R/overreach.log 2>&1; echo OVERREACH rc=$?; head -5 $R/overreach.log
