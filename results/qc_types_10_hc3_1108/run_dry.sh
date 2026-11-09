#!/bin/bash
# QC-TYPES-10/HC3 advisory dry path kit-rtl -> kit_topology -> gen phys -> gen_lint for one hc3 type on bind_hc3
# (same commands as tools/autopilot/kit_wave.py for qwen_compute, plan v4w, src kw35/src_c303p; prov overlay skipped)
set -u
T=${1:-slw_hc3__cld86a7ad4}
H=/srv/opentallas-scratch2/claude/qct10/hc3
src=/srv/opentallas-scratch2/claude/kw35/src_c303p
plan=/srv/opentallas-scratch2/claude/kw35/qcplan_v4w/plan_qc53v4w.json
bind=$H/bind_hc3
asb=$H/src_hc3/physical/die_plan/qwen_compute/qc_start_1106/runtime/asbuilt_hc3.json
W=$H/dry/$T; rm -rf $W; mkdir -p $W
cd $src
st(){ echo "== $1 $(date)"; }
st kit_rtl; python3 tools/die_plan/bind.py kit-rtl $plan --out $bind --asbuilt $asb --type $T --kit $W/rtl > $W/kit_rtl.log 2>&1; echo "RC kit_rtl $?"
st kit_topology; python3 -I $src/tools/die_plan/kit_topology.py prepare-stations $plan $T $W/rtl --native-plan $plan --asbuilt $asb > $W/kit_topology.log 2>&1; echo "RC kit_topology $?"
st gen; ( export OT_FLOW_TAG=flow-20261108-ef-qc; python3 tools/die_plan/gen.py phys $plan --out $W/gen --types $T --rtl-root $src --kit-rtl $T=$W/rtl/kit_rtl.f --hold-ff-margin 0 --max-wire-um 120 --clock-landing /srv/opentallas-scratch2/claude/kw27/src_02909_qc4/physical/die_plan/qwen_compute/qc_start_1106/runtime/sidecar.json ) > $W/gen.log 2>&1; echo "RC gen $?"
K=$W/gen/$T; pdir=$W/plandir; rm -rf $pdir; mkdir -p $pdir; for f in $(dirname $plan)/*; do ln -s "$f" $pdir/; done; ln -sfn $plan $pdir/die_plan.json
st gen_lint; python3 tools/die_plan/kit_gen_lint.py $K --plan-dir $pdir --mem 8 > $W/gen_lint.log 2>&1; echo "RC gen_lint $?"
grep -c "ot_qfd_xs_leaf_fo32 " $W/rtl/*_bound.sv 2>/dev/null; grep -l "module ot_qfd_xs_leaf_fo32" -r $W/rtl $K/rtl 2>/dev/null | head -3
tail -3 $W/gen_lint.log; date
