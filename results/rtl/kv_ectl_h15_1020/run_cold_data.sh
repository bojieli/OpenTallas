#!/bin/bash
set -eu
R=$PWD
E=$R/results/rtl/kv_ectl_h15_1020
S=$R/rtl/qwen_sys/split_20261014
K=$R/rtl/qwen_sys/static_kv_20261014
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
for age in 15;do
 "$V" --binary --timing -j 2 --x-initial unique --x-assign unique -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD \
 -DOT_MEM_NO_INIT -GHXK=$age --top-module tb_ectl_c_h15_cold_data -Mdir "$E/obj_cold_data_$age" \
 "$E/tb_ectl_c_h15_cold_data.sv" "$E/bench_frame_h15.sv" "$K/qkd_ectl_c_st_h15.sv" \
 "$S/qkd_ectl_a_tp8_epoch_direct.sv" "$S/qkd_ectl_native_direct_tp8.sv" \
 "$R/rtl/hdc/nearhbm/ot_qkd_ectl_parts.sv" "$R/rtl/hdc/nearhbm/ot_qwen_nearhbm_attn_stack_h.sv" \
 "$R/rtl/hdc/ot_hdc_delay.sv" "$R/rtl/lib/ot_rst_relay.sv" \
 "$R/physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v" > "$E/build_cold_data_$age.log" 2>&1
 for seed in 11 19;do
 "$E/obj_cold_data_$age/Vtb_ectl_c_h15_cold_data" +verilator+seed+$seed +verilator+rand+reset+2 > "$E/cold_data_seed$seed.log" 2>&1
 grep '^ECTL_C_H15_COLD_DATA_PASS' "$E/cold_data_seed$seed.log"
 done
done
