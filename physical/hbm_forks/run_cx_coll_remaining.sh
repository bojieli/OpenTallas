#!/bin/bash
set -eu
O=$(readlink -m "$1");mkdir -p "$O"
FX=${2:?existing pinned TP96 fixtures}
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
M=physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v
SRC="rtl/link/ot_link_afifo.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hbm_accel/ha2_ar/ot_ha2_prims.sv $M rtl/hbm_accel/tu/ot_hcoll_sram_prims.sv rtl/hbm_accel/tu/ot_hcoll_port.sv rtl/hbm_accel/tu/ot_hbm_accel_tu_endpoint_ps.sv rtl/hbm_accel/tu/ot_hbm_accel_tu_endpoint_psg.sv"
for group in 2 4;do
 lg=1; [ "$group" = 4 ] && lg=2
 "$V" --binary --timing -j 4 -Wno-fatal -Wno-lint --top-module tb_hbm_accel_tu_endpoint --Mdir "$O/m$group" +define+TU_DUT=ot_hbm_accel_tu_endpoint_psg +define+TU_NC=$group +define+TU_NOG=$((96/group)) +define+TU_GSZ +define+TU_REDUCE +define+TU_GSZPORT=$lg +define+TU_PFMAX=64 +define+TU_PCLK_IS_CLK +define+OT_COLL_MUT_GSZ_PAD -GT_PHY=0.833333 $SRC rtl/hbm_accel/tu/tb_hbm_accel_tu_endpoint.sv > "$O/build_m$group.log" 2>&1
 for rank in 0 1;do
  set +e; "$O/m$group/Vtb_hbm_accel_tu_endpoint" +VEC="$FX/g$group" +PF=16 +RANK=$rank +SEED=1 > "$O/pad_${group}_${rank}.log" 2>&1;rc=$?;set -e
  test "$rc" != 0;grep -q PAD_PROGRESS "$O/pad_${group}_${rank}.log"
  echo "PAD group=$group rank=$rank rc=$rc consuming PASS" >> "$O/verdict.txt"
 done
done
for mode in positive mutant;do
 D="";[ "$mode" = mutant ] && D="+define+OT_COLL_MUT_MODE_GUARD"
 "$V" --binary --timing -j 4 -Wno-fatal -Wno-lint --top-module tb_hgi_coll_mode_guard --Mdir "$O/$mode" $D $SRC rtl/hbm_accel/tu/tb_hgi_coll_mode_guard.sv > "$O/build_$mode.log" 2>&1
 set +e;"$O/$mode/Vtb_hgi_coll_mode_guard" > "$O/mode_$mode.log" 2>&1;rc=$?;set -e
 if [ "$mode" = positive ];then test "$rc" = 0;grep -q "MODE_GUARD PASS" "$O/mode_$mode.log";else test "$rc" != 0;grep -q BAD_MODE "$O/mode_$mode.log";fi
 echo "MODE $mode rc=$rc PASS" >> "$O/verdict.txt"
done
echo "CX_COLL_REMAINING PASS" >> "$O/verdict.txt"
