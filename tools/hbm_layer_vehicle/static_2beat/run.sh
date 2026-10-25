#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/../../.."
O=$(realpath "$1");mkdir -p "$O"
V=/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator
for mode in base phasefault sidefault highmut lowmut phasemut validholdmut ne dupfault link3 link4;do
 args=();case "$mode" in phasefault)args=(-GBAD_PHASE=1);;sidefault)args=(-GBAD_PHASE=2);;link3)args=(-GLINK_STAGES=3);;link4)args=(-GLINK_STAGES=4);;highmut)args=(-GMUT=1);;lowmut)args=(-GMUT=2);;phasemut)args=(-GMUT=3);;validholdmut)args=(-GMUT=4);;ne)args=(-GW=2709);;dupfault)args=(-GW=2709 -GDUP_MUT=1);;esac
 "$V" --binary --timing -j 2 -O1 -Wno-fatal --top-module tb "${args[@]}" --Mdir "$O/obj_$mode" rtl/hbm_accel/generic/transport/ot_hbm_static_2beat.sv tools/hbm_layer_vehicle/static_2beat/tb.sv > "$O/$mode.build.log" 2>&1
 set +e
 "$O/obj_$mode/Vtb" > "$O/$mode.log" 2>&1
 rc=$?
 set -e
 echo "$rc" > "$O/$mode.exit"
 case "$mode" in highmut|lowmut|phasemut|validholdmut)test "$rc" != 0;grep -q '2BEAT FAIL' "$O/$mode.log";;*)test "$rc" = 0;grep '2BEAT PASS' "$O/$mode.log";;esac
done
echo 'STATIC2BEAT SUITE PASS NW/NE DATA+CTL exact+odd/even channel depths+DATA/CTL phasefault gates+4mutants' | tee "$O/done"
