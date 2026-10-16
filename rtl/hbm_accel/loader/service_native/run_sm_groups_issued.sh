#!/usr/bin/env bash
# H-DIE 2026-10-15: hardware-issued service groups (tb_hbm_svc_sm_groups_issued) + mutants.
#   run_sm_groups_issued.sh <out> <images> [stack] [rows] [epochs]
set -euo pipefail
ulimit -c 0
out=${1:?out}; images=${2:?images}; stack=${3:-0}; rows=${4:-64}; epochs=${5:-8}
mkdir -p "$out"
d=rtl/hbm_accel/loader/service_native
src=(rtl/lib/ot_reset_sync.sv rtl/lib/ot_rst_relay.sv "$d/ot_hbm_svc_async_fifo.sv" "$d/ot_hbm_svc_prefetch_mapped4_owner.sv" "$d/ot_hbm_svc_prefetch_overlap_owner.sv" "$d/ot_hbm_svc_sm8_landing_bank.sv" "$d/ot_hbm_svc_sm4pc_cdc.sv" "$d/ot_hbm_svc_static_sm_packed136.sv" "$d/ot_hbm_svc_sm_feed_programmed.sv" "$d/ot_hbm_svc_sm_issuer.sv" "$d/ot_hbm_svc_sm_group.sv" rtl/hbm_accel/sm/static/ot_smh_static_feed.sv rtl/hbm_accel/sm/static/ot_smh_calendar_static.sv physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v physical/asap7_memory_macros_v2/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v rtl/model_ready_hbm_r14/ot_hbm_r14_stream_pc.sv "$d/ot_hbm_svc_pc_ctrl_leaf.sv" "$d/ot_hbm_svc_native_sector_pipeline_leaves.sv" "$d/tb_hbm_svc_command_dram_pipeline_fixture.sv" "$d/tb_hbm_svc_sm_groups_issued.sv")
build(){ verilator --binary --timing -j 4 -Wno-fatal $1 --top-module tb_hbm_svc_sm_groups_issued -GSTACK="$stack" -GROWS="$rows" -GEPOCHS="$epochs" --Mdir "$out/$2" -o sim "${src[@]}" > "$out/$2.build.log" 2>&1; }
build "" obj
"$out/obj/sim" +IMAGES="$images" > "$out/positive.log"
grep -q 'SM_GROUPS_ISSUED PASS' "$out/positive.log"
if "$out/obj/sim" +IMAGES="$images" +EARLY > "$out/early_mutant.log" 2>&1;then echo 'early programme mutant survived';exit 1;fi
grep -q 'SM_STACK DUT fault' "$out/early_mutant.log"
build "-DOT_ISSUER_MUT_NORESIDENT" obj_mut
if "$out/obj_mut/sim" +IMAGES="$images" > "$out/noresident_mutant.log" 2>&1;then echo 'copy-before-resident issuer mutant survived';exit 1;fi
grep -q 'SM_STACK' "$out/noresident_mutant.log"
grep -v '^- ' "$out/positive.log"
echo 'SM_GROUPS_EARLY_PROGRAMME_MUTANT rejected'
echo "SM_GROUPS_NORESIDENT_ISSUER_MUTANT rejected: $(grep -m1 -o 'SM_STACK[^"]*' "$out/noresident_mutant.log")"
