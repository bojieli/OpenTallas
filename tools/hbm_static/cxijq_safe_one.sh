#!/bin/bash
# LH-SU 10-19: one SAFE_GATHER ij_q equivalence run vs the legacy (hub-lockstep-proven) ij_q. usage: OUT SD MUT
set -uo pipefail
out=$1; sd=$2; mut=$3; mkdir -p "$out"
verilator --version
verilator --binary --timing -j 4 -Wno-fatal --top-module tb_hbm_cxijq_safe -GSD=$sd -GMUT=$mut --Mdir "$out/obj" -o sim \
 rtl/hbm_accel/generic/adapters/static_su/collport/ot_hbm_su_static_cxport_split.sv \
 rtl/hbm_accel/generic/adapters/static_su/collport/tb_hbm_cxijq_safe.sv > "$out/build.log" 2>&1 || { tail -20 "$out/build.log"; exit 2; }
"$out/obj/sim"
