#!/bin/bash
set -eu
O=$(realpath -m "$1");mkdir -p "$O"
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
verilator --version
source physical/ref_tile/dscoll_lane_w_ltr/kit.env
verilator --binary --timing -j 4 -Wno-fatal -Wno-WIDTH -Wno-lint -Wno-style \
 -DOT_S81PH_COLL_TF_CLEANUP --top-module tb_coll_safe2_boundary --Mdir "$O/obj" \
 $SRCS rtl/lib/ot_rst_relay_tree3.sv rtl/lib/ot_sram_oldread_wreg.sv rtl/dsrom_sys/s81_ph/ot_s81ph_link_ep_safe2.sv rtl/dsrom_sys/s81_ph/coll/ot_s81ph_coll_lane_safe2.sv \
 physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1/ot_sram_1r1w_32x128_m1.v \
 physical/asap7_memory_macros_v2/ot_sram_1r1w_512x128_m4_r2c2/ot_sram_1r1w_512x128_m4_r2c2.v \
 rtl/dsrom_sys/s81_ph/test/tb_coll_safe2_boundary.sv > "$O/build.log" 2>&1
"$O/obj/Vtb_coll_safe2_boundary" > "$O/run.log"
cat "$O/run.log"
grep -q '^COLL_BOUNDARY PASS' "$O/run.log"
