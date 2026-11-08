#!/bin/bash
# QC-TYPES-10/CTLM advisory dry path for tt_ctlm (kit_wave.py stage commands: kit-rtl, kit_topology, gen phys, gen_lint)
set -u
D=/srv/opentallas-scratch2/claude/qct10/ctlm; S=$D/src_ctlmfq; P=$D/plan/plan_qc53v4w_ctlmfq.json; B=$D/bind_ctlmfq
A=$S/physical/die_plan/qwen_compute/qc_start_1106/runtime/asbuilt_reach.json; T=tt_ctlm; W=$D/dry/attempt_d1; K=$W/gen/$T
rm -rf $W; mkdir -p $W/logs; cd $S
python3 tools/die_plan/bind.py kit-rtl $P --out $B --asbuilt $A --type $T --kit $W/rtl > $W/logs/kit_rtl.log 2>&1; echo "KIT_RTL rc $?"
python3 -I $S/tools/die_plan/kit_topology.py prepare-stations $P $T $W/rtl --native-plan $P --asbuilt $A > $W/logs/kit_topology.log 2>&1; echo "KIT_TOPOLOGY rc $?"
export OT_CONS_KIT=1; export OT_FLOW_TAG=flow-20261108-ef-qc
PS=; if python3 tools/die_plan/gen.py phys --help 2>/dev/null | grep -q -- --cland-pinslot; then PS='--cland-pinslot all'; fi
python3 tools/die_plan/gen.py phys $P --out $W/gen --types $T --rtl-root $S --kit-rtl $T=$W/rtl/kit_rtl.f $PS --hold-ff-margin 0 --max-wire-um 120 --clock-landing /srv/opentallas-scratch2/claude/kw27/src_02909_qc4/physical/die_plan/qwen_compute/qc_start_1106/runtime/sidecar.json > $W/logs/gen.log 2>&1; echo "GEN rc $?"
test -f $K/config.mk || test -f $K/freeze.json; echo "GEN_KIT rc $?"
pdir=$W/plandir; rm -rf $pdir; mkdir -p $pdir; for f in $(dirname $P)/*; do ln -s "$f" $pdir/; done; ln -sfn $P $pdir/die_plan.json
python3 tools/die_plan/kit_gen_lint.py $K --plan-dir $pdir --mem 8 > $W/logs/gen_lint.log 2>&1; echo "GEN_LINT rc $?"; tail -n 5 $W/logs/gen_lint.log
grep -c u_fifo $K/macro_place.tcl 2>/dev/null; grep -c place_macro $K/macro_place.tcl 2>/dev/null; grep -o "cpub39_1.sv" $W/rtl/kit_rtl.f | head -1; grep cpub39_1 $W/rtl/kit_rtl.f | xargs sha256sum | cut -c1-12
