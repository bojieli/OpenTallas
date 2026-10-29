#!/bin/bash
# DIE-HEAD-17: DIE-HEAD-15 run_ca15.sh (gate run 161.3/182.9) with ONE change: the partition-internal (hd_tile) clock
# insertion LAT_TT/LAT_FF replaces the 250/202.5 budget in every place the shared model reads it:
#   plan clock.common_latency_ps (copy J17 of the same die plan), --sta-core-latency-ff / --core-latency-ff,
#   landed_phase_ocv --core-lat, count_align_plan --corner key.  Tools = MAIN (wt/die-head-17 @ origin/main).
# usage: run_ca17.sh G LAT_TT LAT_FF   (G = copy of die-head-15/clk15 inputs: clk out_TT out_FF plan_rs_fb1.json)
set -u
G=$1; LT=$2; LF=$3; O=$G/ca; rm -rf $O $G/landed_ocv.json $G/ocv_spice.json $G/proof0 $G/proof_f* $G/proof_t $G/proof; mkdir -p $O
W=/srv/opentallas-scratch2/claude/wt/die-head-17; MT=$W/tools/die_plan
I=/srv/opentallas-scratch2/claude/die-head-11/inv
MAP=/srv/opentallas-scratch2/claude/die-head-3/part/map_part.json
J0=/srv/opentallas-scratch2/claude/wt/die-head-1/physical/die_plan/s81_head/die_plan_root_sp5.json
J=$G/die_plan_root_sp5_lat${LT}.json
python3 -c "import json,sys;d=json.load(open(sys.argv[1]));d[\"clock\"][\"common_latency_ps\"]=float(sys.argv[3]);json.dump(d,open(sys.argv[2],\"w\"),indent=1)" $J0 $J $LT
IDREG=/srv/opentallas-scratch2/claude/die-head-7/sta_qc5/bind_idreg.json
cp $I/g5_st/plan_rs_fb1.json $G/
echo START $(date) code $(git -C $W rev-parse --short HEAD) G=$G LAT TT=$LT FF=$LF
python3 $I/mk_proof.py $G $MAP $G/proof0 --tree-path > $G/mk_proof.log 2>&1 || { echo MKPROOF_FAIL; exit 1; }
cp -r $G/proof0 $G/proof_t
for C in TT FF; do
  python3 $MT/tap_fall_merge.py $G/proof_t $C $G/out_$C/arr_$C.txt --tree $G/clk/tree.json --out $G/proof_f$C > $G/fall_$C.log 2>&1 || { echo FALL_FAIL $C; tail -5 $G/fall_$C.log; exit 1; }
  cp $G/proof_f$C/tap_arrivals_$C.json $G/proof_t/
done
P=$G/proof
python3 $MT/start_stage_emit.py proof $G/proof_t --stages /srv/opentallas-scratch2/claude/die-head-15/st_emit/start_stages.json --arr TT=$G/out_TT/arr_TT.txt --arr FF=$G/out_FF/arr_FF.txt --out $P > $G/st_proof.log 2>&1 || { echo STPROOF_FAIL; tail -5 $G/st_proof.log; exit 1; }
python3 $W/tools/s81_head/landed_phase_ocv.py $G/plan_rs_fb1.json $G --tools $MT --clock-cell inv2 --core-lat TT=$LT,FF=$LF --out $G/landed_ocv.json > $G/landed_ocv.log 2>&1 || { echo LOCV_FAIL; tail -3 $G/landed_ocv.log; exit 1; }
python3 /srv/opentallas-scratch2/claude/nc-headpart/scripts/spice_scale.py $G/landed_ocv.json $G/ocv_spice.json
cd $MT
python3 count_align_plan.py $G/ocv_spice.json --corner TT_droop-regions_corelat${LT},FF_droop-regions_corelat${LF} --mc-chips 2000 --start-skew 57.5,89.7 --sta-proof $P --sta-plan $J \
  --sta-clock-cal spice --sta-cppr-lca --sta-clock-ocv table --sta-clock-droop shared --sta-droop-regions $P/droop_regions.json \
  --sta-core-latency-ff $LF --start-tree clock --start-clean width --sta-clock-cell inv2 ${PLANX:-} --out $O/plan.json > $O/plan.log 2>&1; echo "PLAN_RC $?"
python3 /srv/opentallas-scratch2/claude/die-head-12/plansum.py $O/plan.json
python3 count_align_bind.py $O/plan.json --parts region --out $O/bind.json > $O/bind.log 2>&1; echo "BIND_RC $?"
python3 /srv/opentallas-scratch2/claude/die-head-12/idreg.py $O/bind.json $IDREG $O/bind_idreg.json
python3 die_sta_related.py $P --plan $J --out $O/sta --corner TT --corner FF --core-latency-ff $LF \
  --droop-regions $P/droop_regions.json --count-align $O/bind_idreg.json --count-align-key region --clock-cal spice \
  --cppr-lca --clock-ocv table --clock-droop shared --clock-cell inv2 > $O/sta.log 2>&1; echo "STA_MAIN_RC $?"
grep -E "COUNT-ALIGN|intra |seam " $O/sta.log | cut -c1-300
echo END $(date)
