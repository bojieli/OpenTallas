#!/bin/bash
# S81-TILES-E 10-20 COLL s7: safe4 pair (reference) + safe7 (REACH=1 relay hops) pair transactional scoreboard
# (tb_coll_reach7), Verilator 5.050.  $1 = output dir, $2 = mutant (0 positive; 5 second rx landing hop never loads
# its beat; 6 core landing data never loads; 7 reverse-frame relay drops every frame).
# Mutants 1-4 of the shared safe4 submodules stay on tb_coll_safe4_boundary (coll_safe4_boundary.sh).
set -eu
O=$(realpath -m "$1"); M=${2:-0}; mkdir -p "$O"
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
verilator --version
source physical/ref_tile/dscoll_lane_w_ltr/kit.env
D=()
[ "${OT_COLL_NATIVE32:-0}" != 1 ] || D+=(-DOT_COLL_NATIVE32)
[ "${OT_COLL_NATIVE32_OFF:-0}" != 1 ] || D+=(-DOT_COLL_NATIVE32_OFF)   # v8 offset-register successor (needs OT_COLL_NATIVE32)
if [ "$M" = 5 ]; then D+=(-DOT_COLL_REACH_MUT_LR); fi
if [ "$M" = 6 ]; then D+=(-DOT_COLL_REACH_MUT_LO); fi
if [ "$M" = 7 ]; then D+=(-DOT_COLL_REACH_MUT_RT); fi
verilator --binary --timing -j 4 -Wno-fatal -Wno-WIDTH -Wno-lint -Wno-style -Wno-MULTIDRIVEN \
 -DOT_S81PH_COLL_TF_CLEANUP "${D[@]}" --top-module tb_coll_reach7 --Mdir "$O/obj" \
 $SRCS rtl/lib/ot_rst_relay_tree3.sv rtl/lib/ot_sram_oldread_b64.sv rtl/lib/ot_sram_showahead_b64.sv \
 rtl/common/ot_link_credit_rx_b64.sv rtl/common/ot_link_credit_tx_rc.sv \
 rtl/dsrom_sys/s81_ph/ot_s81ph_link_ep_safe4.sv rtl/dsrom_sys/s81_ph/ot_s81ph_link_gbx_safe3.sv \
 rtl/dsrom_sys/s81_ph/coll/ot_s81ph_coll_lane_safe4.sv \
 physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1/ot_sram_1r1w_32x128_m1.v \
 physical/asap7_memory_macros_v2/ot_sram_1r1w_512x128_m4_r2c2/ot_sram_1r1w_512x128_m4_r2c2.v \
 physical/asap7_memory_macros_v2/ot_sram_1r1w2c_32x64_m1/ot_sram_1r1w2c_32x64_m1.v \
 physical/asap7_memory_macros_v2/ot_sram_1r1w2c_256x64_m1/ot_sram_1r1w2c_256x64_m1.v \
 rtl/dsrom_sys/s81_ph/test/tb_coll_reach7.sv > "$O/build.log" 2>&1 || { tail -40 "$O/build.log"; exit 2; }
set +e
"$O/obj/Vtb_coll_reach7" > "$O/run.log" 2>&1
rc=$?
set -e
tail -30 "$O/run.log"
echo "sim exit $rc"
grep -q '^COLL_REACH7 PASS' "$O/run.log"
