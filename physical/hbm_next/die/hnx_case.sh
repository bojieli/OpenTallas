#!/bin/bash
# HBM-NEXT-DIE 10-19: early die-level integration of the P = 4 frame with stand-ins (relay-free placement case, the
# GEN2a form): GEN2 pre-relay contract (1,214 instances) + GEN2 views (SM = the P = 1 smh_attn view as the stand-in
# inside the P = 4 column slot) on the hnx plan / grants / region map; regional clocks, die repeaters at 405, reset gate
# in diag mode.  Forked by copy from results/arch/hbm_die_d4g/gen2/gen_d4g2.sh (no GEN2 edits).
#   usage (on the fleet, cwd = the case dir holding src/ and views/):  bash hnx_case.sh <tag>
set -o pipefail
TAG=${1:-f4c}
R=$(cd "$(dirname "$0")" && pwd); cd $R/src || exit 9
CASE=case_$TAG
rm -rf $R/$CASE $R/gen_$CASE.log
D=physical/hbm_next/die/$TAG; PL=results/arch/hbm_next_1019/die/plan/$TAG
SM=wbk_SW=wbk_SW,wbk_NW=wbk_NW,sfup_SW=sfup_SW,sfup_SE=sfup_SE,sfup_NW=sfup_NW,sfup_NE=sfup_NE,refcfg_SW=refcfg_SW,refcfg_NW=refcfg_NW
# step 5 (10-19): score quarters into their per-quadrant IDX-corner slots (placed before relay lane rows; tags >= f4c_t8)
grep -q "\"idxs_SW\"" $D/grants_hnx_$TAG.json && SM=$SM,hb_idx__s_SW=idxs_SW,hb_idx__s_SE=idxs_SE,hb_idx__s_NW=idxs_NW,hb_idx__s_NE=idxs_NE
# L2H-P3 10-19: HC bank tiles hcb_Qk into their explicit racetrack grant slots hcbk_Qk (tags with hcbk_* slots, e.g. f4c_t9p3r)
grep -q "\"hcbk_SW0\"" $D/grants_hnx_$TAG.json && for q in SW SE NW NE; do for k in 0 1 2 3 4 5 6 7; do SM=$SM,hcb_$q$k=hcbk_$q$k; done; done
OT_ABS_PIN_WINDOW_UM=3 OT_RESET_GATE=diag PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 MPLBACKEND=Agg /usr/bin/time -v python3 tools/hbm_die_v15/die_case_v16.py \
  --views $R/views --out $R/$CASE --contract $R/views/contract.json --plan $PL/compact.P.json --lanes $PL/lanes.json \
  --grants $D/grants_hnx_$TAG.json --compact-pins --max-pin-density 6 --die-repeaters --max-wire-um 405 --hold-budget die --paths 2000000 \
  --slot-map $SM --clock-mode hbm=regional,stream=regional,serial=regional --clock-region-map $D/region_map_hnx_$TAG.json \
  --clock-near-um 405 --clock-region-max-um 4000 --diagnostic-param-alias > $R/gen_$CASE.log 2>&1 || { echo GEN_FAIL; grep -v '^\s' $R/gen_$CASE.log | tail -25; exit 3; }
echo GEN_OK $CASE; grep -E '^(clock|clock_check|clock_regions|reset_reach_gate|lane rows) ' $R/gen_$CASE.log; grep -v '^\s' $R/gen_$CASE.log | tail -6
python3 tools/hbm_die_v15/d4f_overreach.py $R/$CASE $R/views/contract.json --out $R/overreach_$CASE.json > $R/overreach_$CASE.log 2>&1; echo OVERREACH rc=$?; head -8 $R/overreach_$CASE.log
exit 0
