#!/bin/bash
# HBM-GENREACH 10-20: GEN2c/GEN2d die case (= the gen_d4g2c.sh recipe of artifacts d4g_gen2c, same arguments) with the reach
# fix: die_case_v16 --lane-reach (default fail: reach-bounded lane rows + bounded relay homes + placed-hop audit; GEN stops
# with GEN_REACH_FAIL naming every bus it cannot keep <= 405 um) and the post-GEN per-bus pin check d4g_reach_check.py.
#   OT_GEN2_CASE   case dir name (default case)          OT_LANE_REACH  fail (default) | diag | legacy
#   OT_REACH_GATE  fail (default: the case FAILS on any sync / forwarded bus over reach) | diag
#   OT_DIE_CASE_EXTRA  extra die_case args (--prior-place / --reserve-homes ...)
# Prints GEN_OK only when GEN finished AND the reach check passed (or OT_REACH_GATE=diag -> GEN_OK_REACH_DIAG + GEN_OK).
set -o pipefail
export OT_ABS_PIN_WINDOW_UM=${OT_ABS_PIN_WINDOW_UM:-3}
R=$(cd "$(dirname "$0")" && pwd); cd $R/src
CASE=${OT_GEN2_CASE:-case}; LR=${OT_LANE_REACH:-fail}; RG=${OT_REACH_GATE:-fail}
rm -rf $R/$CASE $R/gen_$CASE.log
D=results/arch/hbm_die_d4g
SM=wbk_SW=wbk_SW,wbk_NW=wbk_NW,sfup_SW=sfup_SW,sfup_SE=sfup_SE,sfup_NW=sfup_NW,sfup_NE=sfup_NE,refcfg_SW=refcfg_SW,refcfg_NW=refcfg_NW
OT_RESET_GATE=${OT_RESET_GATE:-diag} PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 MPLBACKEND=Agg /usr/bin/time -v python3 tools/hbm_die_v15/die_case_v16.py \
  --views $R/views --out $R/$CASE --contract $R/views/contract.json --plan $D/plan/d4g_phy/compact.P.json --lanes $D/plan/d4g_phy/lanes.json \
  --grants $D/grants_d4g.json --compact-pins --max-pin-density 6 --die-repeaters --max-wire-um 405 --hold-budget die --paths 2000000 \
  --slot-map $SM --clock-mode hbm=regional,stream=regional,serial=regional --clock-region-map $D/d4g_region_map.json \
  --clock-near-um 405 --clock-region-max-um 4000 --diagnostic-param-alias --lane-reach $LR ${OT_DIE_CASE_EXTRA} > $R/gen_$CASE.log 2>&1 || {
    grep -q GEN_REACH_FAIL $R/gen_$CASE.log && echo GEN_REACH_FAIL $CASE; echo GEN_FAIL; grep -v '^\s' $R/gen_$CASE.log | tail -20 | cut -c1-2500; exit 3; }
echo GEN_DONE $CASE; grep -E '^(clock|clock_check|clock_regions|reset_reach_gate|lane rows|reach audit|prior homes|reserved) ' $R/gen_$CASE.log | cut -c1-1500; grep -v '^\s' $R/gen_$CASE.log | tail -4
python3 tools/hbm_die_v15/d4f_overreach.py $R/$CASE $R/views/contract.json --out $R/overreach_$CASE.json > $R/overreach_$CASE.log 2>&1; echo OVERREACH rc=$?; head -5 $R/overreach_$CASE.log
python3 tools/hbm_die_v16/d4g_reach_check.py $R/$CASE $R/views/contract.json --out $R/reach_check_$CASE.json --fix $R/reach_fix_$CASE.json \
  --all $R/reach_all_$CASE.json > $R/reach_check_$CASE.log 2>&1; rc=$?; grep '^REACH_CHECK' $R/reach_check_$CASE.log | cut -c1-1500
[ "$CASE" = case ] && cp $R/overreach_case.json $R/overreach.json
if [ $rc != 0 ]; then
  [ "$RG" = fail ] && { echo "GEN_REACH_FAIL $CASE post-GEN reach check (per bus): $R/reach_check_$CASE.json"; echo GEN_FAIL; exit 4; }
  echo GEN_OK_REACH_DIAG $CASE
fi
echo GEN_OK $CASE
exit 0
