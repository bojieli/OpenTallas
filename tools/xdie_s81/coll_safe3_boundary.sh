#!/bin/bash
# S81-COLL bank64 safe3: legacy P1 lane pair vs safe3 lane pair miter (tb_coll_safe3_boundary), Verilator 5.050.
# $1 = output dir, $2 = mutant (0 positive; 1 b64 OLD-read forwarding removed; 2 b64 same-address read not suppressed
# (must hit the COLL_COLLISION_UNSAFE fatal); 3 gearbox rem select one cycle stale; 4 gearbox hold select stale)
set -eu
O=$(realpath -m "$1"); M=${2:-0}; mkdir -p "$O"
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
verilator --version
source physical/ref_tile/dscoll_lane_w_ltr/kit.env
D=()
if [ "$M" = 1 ]; then D+=(-DOT_S81PH_OLDREAD_MUT); fi
if [ "$M" = 2 ]; then D+=(-DOT_S81PH_B64_COLLIDE_MUT); fi
if [ "$M" = 3 ]; then D+=(-DOT_S81PH_GBX3_MUT=1); fi
if [ "$M" = 4 ]; then D+=(-DOT_S81PH_GBX3_MUT=2); fi
verilator --binary --timing -j 4 -Wno-fatal -Wno-WIDTH -Wno-lint -Wno-style -Wno-MULTIDRIVEN \
 -DOT_S81PH_COLL_TF_CLEANUP "${D[@]}" --top-module tb_coll_safe3_boundary --Mdir "$O/obj" \
 $SRCS rtl/lib/ot_rst_relay_tree3.sv rtl/lib/ot_sram_oldread_b64.sv rtl/lib/ot_sram_showahead_b64.sv \
 rtl/common/ot_link_credit_rx_b64.sv rtl/common/ot_link_credit_tx_rc.sv \
 rtl/dsrom_sys/s81_ph/ot_s81ph_link_ep_safe3.sv rtl/dsrom_sys/s81_ph/ot_s81ph_link_gbx_safe3.sv \
 rtl/dsrom_sys/s81_ph/coll/ot_s81ph_coll_lane_safe3.sv \
 physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1/ot_sram_1r1w_32x128_m1.v \
 physical/asap7_memory_macros_v2/ot_sram_1r1w_512x128_m4_r2c2/ot_sram_1r1w_512x128_m4_r2c2.v \
 physical/asap7_memory_macros_v2/ot_sram_1r1w2c_32x64_m1/ot_sram_1r1w2c_32x64_m1.v \
 physical/asap7_memory_macros_v2/ot_sram_1r1w2c_256x64_m1/ot_sram_1r1w2c_256x64_m1.v \
 rtl/dsrom_sys/s81_ph/test/tb_coll_safe3_boundary.sv > "$O/build.log" 2>&1 || { tail -40 "$O/build.log"; exit 2; }
set +e
"$O/obj/Vtb_coll_safe3_boundary" > "$O/run.log" 2>&1
rc=$?
set -e
tail -30 "$O/run.log"
echo "sim exit $rc"
grep -q '^COLL_SAFE3_BOUNDARY PASS' "$O/run.log"
