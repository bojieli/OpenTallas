#!/bin/bash
# DIE-HEAD-15: new 170-stage emit; (copy of run_ca13.sh on MAIN 013a9a8543 incl. CLK-INV-CAL-1; gate clock cell inv2 declared, no cal_tools fork):
# DIE-HEAD-12: HEAD inv2 rep200 (+ start-stage taps) CA re-plan on MAIN tools (aec2b2f471 + approved rootcnt 536c703e0f
# + FLOW-ONEMODEL-3 08351abc28, local merge in wt/die-head-12-run, never pushed; + DIE-HEAD-12 stage-tap fall fix).
# Arrivals = FLOW-ONEMODEL-2 both-edge readout (T/F per tap, N/M per clock cell) from a fresh combo GRT (G/out_{TT,FF}).
# Order: mk_proof (rise) -> tap_fall_merge --tree (tap + node falls) -> start_stage_emit proof (stage taps, rise + fall).
set -u
G=${1:-/srv/opentallas-scratch2/claude/die-head-15/clk15}; O=$G/ca; rm -rf $O $G/landed_ocv.json $G/ocv_spice.json $G/proof0 $G/proof_f* $G/proof_t $G/proof; mkdir -p $O
W=/srv/opentallas-scratch2/claude/wt/die-head-15; MT=$W/tools/die_plan; CT=/srv/opentallas-scratch2/claude/die-head-12/cal_tools/tools/die_plan
I=/srv/opentallas-scratch2/claude/die-head-11/inv
MAP=/srv/opentallas-scratch2/claude/die-head-3/part/map_part.json
J=/srv/opentallas-scratch2/claude/wt/die-head-1/physical/die_plan/s81_head/die_plan_root_sp5.json
IDREG=/srv/opentallas-scratch2/claude/die-head-7/sta_qc5/bind_idreg.json
cp $I/g5_st/plan_rs_fb1.json $G/
echo START $(date) code $(git -C $W rev-parse --short HEAD) G=$G
python3 $I/mk_proof.py $G $MAP $G/proof0 --tree-path > $G/mk_proof.log 2>&1 || { echo MKPROOF_FAIL; exit 1; }
cp -r $G/proof0 $G/proof_t
for C in TT FF; do
  python3 $MT/tap_fall_merge.py $G/proof_t $C $G/out_$C/arr_$C.txt --tree $G/clk/tree.json --out $G/proof_f$C > $G/fall_$C.log 2>&1 || { echo FALL_FAIL $C; tail -5 $G/fall_$C.log; exit 1; }
  cp $G/proof_f$C/tap_arrivals_$C.json $G/proof_t/
  python3 -c "import json,sys;d=json.load(open(sys.argv[1]));print(sys.argv[2],'fall',d.get('fall_arrivals'))" $G/proof_t/tap_arrivals_$C.json $C
done
P=$G/proof
python3 $MT/start_stage_emit.py proof $G/proof_t --stages /srv/opentallas-scratch2/claude/die-head-15/st_emit/start_stages.json --arr TT=$G/out_TT/arr_TT.txt --arr FF=$G/out_FF/arr_FF.txt --out $P > $G/st_proof.log 2>&1 || { echo STPROOF_FAIL; tail -5 $G/st_proof.log; exit 1; }
python3 $W/tools/s81_head/landed_phase_ocv.py $G/plan_rs_fb1.json $G --tools $MT --clock-cell inv2 --out $G/landed_ocv.json > $G/landed_ocv.log 2>&1 || { echo LOCV_FAIL; tail -3 $G/landed_ocv.log; exit 1; }
python3 /srv/opentallas-scratch2/claude/nc-headpart/scripts/spice_scale.py $G/landed_ocv.json $G/ocv_spice.json
cd $MT
python3 count_align_plan.py $G/ocv_spice.json --mc-chips 2000 --start-skew 57.5,89.7 --sta-proof $P --sta-plan $J \
  --sta-clock-cal spice --sta-cppr-lca --sta-clock-ocv table --sta-clock-droop shared --sta-droop-regions $P/droop_regions.json \
  --sta-core-latency-ff 202.5 --start-tree clock --start-clean width --sta-clock-cell inv2 ${PLANX:-} --out $O/plan.json > $O/plan.log 2>&1; echo "PLAN_RC $?"
python3 /srv/opentallas-scratch2/claude/die-head-12/plansum.py $O/plan.json
python3 count_align_bind.py $O/plan.json --parts region --out $O/bind.json > $O/bind.log 2>&1; echo "BIND_RC $?"
python3 /srv/opentallas-scratch2/claude/die-head-12/idreg.py $O/bind.json $IDREG $O/bind_idreg.json
python3 die_sta_related.py $P --plan $J --out $O/sta --corner TT --corner FF --core-latency-ff 202.5 \
  --droop-regions $P/droop_regions.json --count-align $O/bind_idreg.json --count-align-key region --clock-cal spice \
  --cppr-lca --clock-ocv table --clock-droop shared --clock-cell inv2 > $O/sta.log 2>&1; echo "STA_MAIN_RC $?"
grep -E "COUNT-ALIGN|intra |seam " $O/sta.log | cut -c1-300
echo END $(date)
