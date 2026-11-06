#!/usr/bin/env bash
set -eu
base=$(pwd)
vl=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
p=results/native_wbk_safe_1106
d=rtl/hbm_accel/cores_split/reform_1106
"$vl" --binary --timing -O1 -j 4 -Wno-fatal -Wno-lint -Wno-style -Wno-MULTIDRIVEN --top-module tb_wbq --Mdir "$base/obj_family" -o sim \
 "$p/tb_native_family.sv" "$p/gold_wb_kport_q.sv" "$p/gold_wb_cutthrough.sv" \
 "$d/ot_wbk_native_safe.sv" "$d/ot_wbk_native_safe_children.sv" "$d/ot_wbk_native_elastic_out.sv" \
 "$d/ot_hbm_face_reg.sv" "$d/ot_hbm_face_rst_relay.sv" rtl/lib/ot_reset_sync.sv \
 rtl/hbm_accel/service/ot_hbm_accel_cdc_fifo.sv rtl/hbm_accel/loader/service_native/ot_hbm_svc_pc_ctrl_leaf.sv \
 physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v > family.build.log 2>&1
"$base/obj_family/sim" > family.run.log 2>&1
