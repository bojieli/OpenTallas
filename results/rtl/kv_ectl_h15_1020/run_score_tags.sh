#!/bin/bash
set -eu
R=$PWD
E=$R/results/rtl/kv_ectl_h15_1020
S=$R/rtl/qwen_sys/split_20261014
K=$R/rtl/qwen_sys/static_kv_20261014
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
for age in 15 14 13;do
 "$V" --binary --timing -j 2 --x-initial unique --x-assign unique -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD \
 -GHXK=$age --top-module tb_ectl_c_h15 -Mdir "$E/obj_$age" \
 "$E/tb_ectl_c_h15.sv" "$E/bench_frame_h15.sv" "$K/qkd_ectl_c_st_h15.sv" \
 "$S/qkd_ectl_a_tp8_epoch_direct.sv" "$S/qkd_ectl_native_direct_tp8.sv" \
 "$R/rtl/hdc/nearhbm/ot_qkd_ectl_parts.sv" "$R/rtl/hdc/nearhbm/ot_qwen_nearhbm_attn_stack_h.sv" \
 "$R/rtl/hdc/ot_hdc_delay.sv" "$R/rtl/lib/ot_rst_relay.sv" \
 "$R/physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v" > "$E/build_$age.log" 2>&1
 set +e
 "$E/obj_$age/Vtb_ectl_c_h15" +verilator+seed+19 +verilator+rand+reset+2 > "$E/run_$age.log" 2>&1
 rc=$?
 set -e
 if [ "$age" = 15 ];then test "$rc" = 0;grep '^ECTL_SAFE32_CAPTURE_PASS' "$E/run_$age.log"
 else test "$rc" -ne 0;grep SCORE_AGE_MISMATCH "$E/run_$age.log";fi
done
