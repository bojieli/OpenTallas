#!/bin/bash
# TOK-ALL-17: build + run the die_b178 u_s_0S return-lane cone bench: tt, ff, and three mutant controls.
#   run_ret_cone.sh SRC OUT
set -uo pipefail
SRC=$(realpath "$1"); O=$(realpath -m "$2"); mkdir -p "$O"; cd "$SRC"
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
LP=${LAND_PLAN:-/srv/opentallas-scratch2/claude/tok-ds-12-1027/veh/tree_b178/results/arch/s81_dv_1016/landing/p4l/land_plan.json}
python3 tools/s81_dv/tokfunc/die_ret_cone.py physical/die_plan/s81/bind/inputs/die_b178.v "$O/ret_cone.sv" \
    0L01,0L02,0L03,0R01,0R02,0R03 "$LP" > "$O/ret_cone.json" || exit 2
F="rtl/dsrom_sys/s81_glue/ot_s81_rly.sv rtl/dsrom_sys/s81_glue/dsfd_rly_masters_gen18.sv rtl/dsrom_sys/s81_glue/dsfd_rly_masters_dv276.sv
   rtl/dsrom_sys/s81_glue/dsfd_rly_masters_dvh.sv rtl/dsrom_sys/s81_dv/land/dsfd_dvland.sv rtl/dsrom_sys/s81_dv/land/ot_s81_land.sv
   $O/ret_cone.sv tools/s81_dv/tokfunc/tb_ret_cone.sv"
sha256sum $F physical/die_plan/s81/bind/inputs/die_b178.v "$LP" > "$O/sources.sha256"
for v in tt: ff:+define+FRAME_CAL_FF mutsel:+define+OT_S81_LAND_MUT_SEL mutfwd:+define+OT_DVRLYH_MUT mutrs:+define+OT_S81_RLY_RSMUT; do
  n=${v%%:*}; d=${v#*:}; d=${d//+define+/-D}
  "$V" --binary --timing -O1 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD -Wno-lint -Wno-style -Wno-MULTIDRIVEN $d \
     --top-module tb_ret_cone -Mdir "$O/obj_$n" $F --build-jobs 8 > "$O/build_$n.log" 2>&1 || { echo "BUILD FAIL $n"; tail -20 "$O/build_$n.log"; continue; }
  "$O/obj_$n/Vtb_ret_cone" > "$O/run_$n.log" 2>&1
  echo "== $n: $(grep -E '^RC lane|RC_END' "$O/run_$n.log" | tr '\n' ' ')"
done
