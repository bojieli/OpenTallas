#!/bin/bash
# FABLE-FIX-HEAD-CORRIDOR: candidate stage rects on HEAD-PLAN-R4's rs7 composition (g1e + KCRED 28 + r564 rows + strap sites, main be66cd6f tools), then the
# rs-series gate chain (republish, receipt, kit RTL, bind, cohort, LATCHECK, G0), all outputs in this lane.
# usage: run_gate.sh RUN CANDIDATE_PLAN
set -u; L=/srv/opentallas-scratch2/claude/head-die-r/nf15e_e10; F=/srv/opentallas-scratch2/claude/fable-fix-head-corridor
RUN=${1:?run}; CAND=${2:?candidate}; P=$F/prep_$RUN; O=$F/gates_$RUN; [ ! -e $P ] || { echo "$P exists"; exit 79; }
cp -a $L/hr4/prep_rs7 $P || exit 1; mkdir -p $O $F/code6
for d in native_domains physical results rtl; do [ -e $F/code6/$d ] || ln -s $L/hr4/code_rs6/$d $F/code6/$d; done
[ -e $F/code6/tools ] || cp -a $L/hr4/code_rs6/tools $F/code6/tools   # real copy: the bind manifest resolves ../gates_RUN from the tools' repo root
cd $F/code6
{ python3 -I $F/apply_stage_rects.py $CAND $P/source_plan.json $P/source_plan.cols.json $O/stage_rect_patch.json && mv $P/source_plan.cols.json $P/source_plan.json \
  && python3 -I -c "import sys,runpy;sys.path.insert(0,'tools/die_plan');sys.argv=['schema.py','validate','$P/source_plan.json'];runpy.run_path('tools/die_plan/schema.py',run_name='__main__')" | tail -1 \
  && HR4_CODE=$L/hr4/code_rs6 python3 -I $L/hr4/republish_g1.py $P; } > $O/compose.log 2>&1; rc=$?; tail -2 $O/compose.log | cut -c1-600; echo COMPOSE_RC=$rc; [ $rc = 0 ] || exit 1
echo "PLAN_SHA $(sha256sum $P/source_plan.json | cut -c1-16)"
python3 -I tools/s81_head/head_native_release_receipt.py --plan $P/source_plan.json --proof-dir /srv/opentallas-scratch2/claude/head-die-r/native_release_proof --out $F/native_receipt_$RUN > $O/receipt.log 2>&1; echo RECEIPT_RC=$?
python3 -I tools/s81_head/head_wave_kit_rtl.py export --plan $P/source_plan.json --out $F/kit_rtl_${RUN}_hd_lep0N --type hd_lep0N > $O/kit_rtl_hd_lep0N.log 2>&1; echo KIT_RTL_RC=$?
python3 -I tools/s81_head/head_die_portbind.py $P/source_plan.json --clock-landing $P/source_sidecar.json --out ../gates_$RUN/bind > $O/bind.log 2>&1; B=$?; echo BIND_RC=$B
if [ $B = 0 ]; then
python3 -I tools/s81_head/head_gen_cohort.py $P $O/bind/gen --json $O/cohort.json > $O/cohort.log 2>&1; echo COHORT_RC=$?
python3 -I tools/die_plan/gen_lane_latcheck.py $P/source_plan.json --rtl $P/published --rtl $O/bind/gen --landings $O/bind/gen/gen_clock_landings.json --fixed-in-core --tsv $O/latcheck.tsv --json $O/latcheck.json > $O/latcheck.log 2>&1; echo LATCHECK_RC=$?
fi
python3 -I tools/die_plan/check.py $P/source_plan.json --native-reset-receipt $F/native_receipt_$RUN/native_release_receipt.json --out $O/g0 --quiet > $O/g0.log 2>&1; echo G0_RC=$?
for f in receipt kit_rtl_hd_lep0N bind cohort latcheck g0; do echo "== $f: $(tail -1 $O/$f.log 2>/dev/null | cut -c1-400)"; done
echo GATE_DONE
