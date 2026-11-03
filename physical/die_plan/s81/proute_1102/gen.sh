#!/bin/bash
# S81-PROUTE-2: pilot kit gen on the wave source (same gen args as the S81 station kits)
set -euo pipefail
W=/srv/opentallas-scratch2/claude/s81-proute-2
WT=/srv/opentallas-scratch2/claude/wt/s81-proute-2
SRC=/srv/opentallas-scratch2/claude/wt/kit-wave-15-s81b
I=/srv/opentallas-scratch2/claude/codex-s81-wave-1345/kit-wave/s81/b1a2125433d0/items
T=slice_station__p7S_x11
rm -rf $W/rtl $W/gen
python3 $WT/physical/die_plan/s81/proute_1102/proute_x11p.py sidecar $SRC/physical/die_plan/s81/h2_2249/landed_sidecar_h2.json $W/landed_sidecar_x11p.json
python3 $WT/physical/die_plan/s81/proute_1102/proute_x11p.py rtl $W/plan_proute_x11p.json \
  $I/slice_station__t30__clcedefe91/attempt_6/rtl/slice_station__t30__clcedefe91_bound.sv \
  $I/slice_station__t30__cl1653104c/attempt_4/rtl/slice_station__t30__cl1653104c_bound.sv $W/libs.f $W/rtl
cd $SRC
python3 tools/die_plan/gen.py phys $W/plan_proute_x11p.json --out $W/gen --types $T --rtl-root $SRC \
  --kit-rtl $T=$W/rtl/kit_rtl.f --hold-ff-margin 0 --max-wire-um 100 \
  --clock-landing $W/landed_sidecar_x11p.json
python3 $WT/physical/die_plan/s81/proute_1102/proute_x11p.py lp $W/gen/$T/landing_placement.tcl \
  $I/slice_station__t30__clcedefe91/attempt_6/gen/slice_station__t30__clcedefe91/landing_placement.tcl \
  $I/slice_station__t30__cl1653104c/attempt_4/gen/slice_station__t30__cl1653104c/landing_placement.tcl $W/rtl/flat_renames.json
ls $W/gen/$T/config.mk
