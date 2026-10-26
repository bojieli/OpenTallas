#!/bin/bash
# H-D4G-GEN2 die case: GEN2 plan (SMFRAME + SFUPLAN + SET 2 + COLLQ slots, grants_d4g.json of claude/hd4g-gen2-1018), regional
# clocks + neighbour-skew gate, die repeaters at 405, lane rows placed as units, SYNTH pin bind (sfucore k9 N-face window).
#   OT_GEN2_CASE=case_a  relay-free placement case (pins / stations / root sites for the relay or landing layer), reset gate diag
#   OT_GEN2_CASE=case    the GEN2 die (relays / landings spliced), reset-reach gate FAIL mode -> GRT2 (case/run.sh)
set -o pipefail
export OT_ABS_PIN_WINDOW_UM=${OT_ABS_PIN_WINDOW_UM:-3}
R=$(cd "$(dirname "$0")" && pwd); cd $R/src
CASE=${OT_GEN2_CASE:-case}
rm -rf $R/$CASE $R/gen_$CASE.log
D=results/arch/hbm_die_d4g
SM=wbk_SW=wbk_SW,wbk_NW=wbk_NW,sfup_SW=sfup_SW,sfup_SE=sfup_SE,sfup_NW=sfup_NW,sfup_NE=sfup_NE,refcfg_SW=refcfg_SW,refcfg_NW=refcfg_NW
OT_RESET_GATE=${OT_RESET_GATE:-fail} PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 MPLBACKEND=Agg /usr/bin/time -v python3 tools/hbm_die_v15/die_case_v16.py \
  --views $R/views --out $R/$CASE --contract $R/views/contract.json --plan $D/plan/d4g_phy/compact.P.json --lanes $D/plan/d4g_phy/lanes.json \
  --grants $D/grants_d4g.json --compact-pins --max-pin-density 6 --die-repeaters --max-wire-um 405 --hold-budget die --paths 2000000 \
  --slot-map $SM --clock-mode hbm=regional,stream=regional,serial=regional --clock-region-map $D/d4g_region_map.json \
  --clock-near-um 405 --clock-region-max-um 4000 --diagnostic-param-alias > $R/gen_$CASE.log 2>&1 || { echo GEN_FAIL; grep -v '^\s' $R/gen_$CASE.log | tail -20; exit 3; }
echo GEN_OK $CASE; grep -E '^(clock|clock_check|clock_regions|reset_reach_gate|lane rows) ' $R/gen_$CASE.log; grep -v '^\s' $R/gen_$CASE.log | tail -4
python3 tools/hbm_die_v15/d4f_overreach.py $R/$CASE $R/views/contract.json --out $R/overreach_$CASE.json > $R/overreach_$CASE.log 2>&1; echo OVERREACH rc=$?; head -5 $R/overreach_$CASE.log
[ "$CASE" = case ] && cp $R/overreach_case.json $R/overreach.json
exit 0
