#!/usr/bin/env bash
set -eu
export PATH=$HOME/.local/opentallas-tools/bin:$PATH
W=$(git -C "$(dirname "$0")" rev-parse --show-toplevel)
R=${1:?supply a scratch run directory}; mkdir -p "$R"
verilator --binary --timing -Wno-fatal -j 4 --top-module tb --Mdir $R/obj_drain $W/results/hbm_bind_3_1029/tb_drain_miter.sv $W/physical/die_plan/hbm/bind/rtl/ot_hgi_su_lgroup2_drain.sv $W/rtl/hbm_accel/generic/peers/ot_hgi_su_unit.sv > $R/drain_build.log 2>&1
$R/obj_drain/Vtb > $R/drain.log 2>&1
$R/obj_drain/Vtb +MUTANT > $R/drain_mutant.log 2>&1
grep -q "PASS drain" $R/drain.log
grep -q "CAUGHT drain" $R/drain_mutant.log
