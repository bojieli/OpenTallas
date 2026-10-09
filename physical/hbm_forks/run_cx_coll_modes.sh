#!/bin/bash
set -eu
O=$(readlink -m "$1");mkdir -p "$O"
bash physical/hbm_forks/run_coll_gsz.sh "$O/gsz" > "$O/groups.log" 2>&1
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
M=physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v
SRC="rtl/link/ot_link_afifo.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hbm_accel/ha2_ar/ot_ha2_prims.sv $M rtl/hbm_accel/tu/ot_hcoll_sram_prims.sv rtl/hbm_accel/tu/ot_hcoll_port.sv rtl/hbm_accel/tu/ot_hbm_accel_tu_endpoint_psg.sv rtl/hbm_accel/tu/tb_hgi_coll_mode_guard.sv"
for mode in positive mutant;do
 D=""; [ "$mode" = mutant ] && D="+define+OT_COLL_MUT_MODE_GUARD"
 $V --binary --timing -j 4 -Wno-fatal --top-module tb_hgi_coll_mode_guard --Mdir "$O/$mode" $D $SRC > "$O/build_$mode.log" 2>&1
 set +e; "$O/$mode/Vtb_hgi_coll_mode_guard" > "$O/$mode.log" 2>&1;rc=$?;set -e
 if [ "$mode" = positive ];then [ "$rc" = 0 ];grep -q "MODE_GUARD PASS" "$O/$mode.log";else [ "$rc" != 0 ];grep -q BAD_MODE "$O/$mode.log";fi
 echo "$mode rc=$rc" >> "$O/verdict.txt"
done
echo "CX_COLL_MODES PASS" >> "$O/verdict.txt"
