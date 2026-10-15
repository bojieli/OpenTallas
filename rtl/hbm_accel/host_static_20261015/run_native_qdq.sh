#!/usr/bin/env bash
set -euo pipefail
ulimit -c 0
out=$1;mut=${2:-0};rows=${3:-1024};mkdir -p "$out"
b=rtl/hbm_accel/tu/lk_ep_20261010
verilator --binary --timing -O2 -j 8 -Wno-fatal -Wno-lint -Wno-style -Irtl/common -Irtl/dsrom_sys/s81_link -DOT_MEM_NO_INIT --top-module tb_hbm_host_static_native_qdq -GMUT="$mut" --Mdir "$out/obj" -o sim \
 rtl/common/{ot_secded,ot_secded_dec_dp}.sv \
 physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v \
 physical/asap7_memory_macros_v2/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v \
 rtl/hbm_accel/tu/link_retry_sram_20261008/ot_hbm_replay_sram_dp.sv \
 rtl/hbm_accel/tu/link_retry_pipeline_20261009/ot_hbm_link_retry_pipeline_cl.sv \
 rtl/dsrom_sys/s81_ph/ot_s81ph_link_gbx.sv \
 "$b"/{hfd_lk_ep,hfd_lk_ep_face,ot_crc_par,ot_hbm_lk_ep,ot_lkep_sub,ot_lkep_ctrl_phy,ot_lkep_ctrl_phy_data,ot_lkep_status_shared,ot_lkep_rx_shared,ot_lkep_tx_shared}.sv \
 rtl/dsrom_sys/s81_link/ot_pdie_serdes.sv rtl/dsrom_sys/s81_link/{ot_s81_kp4_enc,ot_s81_kp4_dec}.sv \
 rtl/hbm_accel/io_native_20261014/{ot_hbm_host_packet,hfd_host_packet_face,ot_hbm_host_landing256,hfd_host_native}.sv \
 rtl/hbm_accel/host_static_20261015/{ot_hbm_host_static_ingress,ot_hbm_program_block_ready,ot_hbm_host_qdq_installed_target,hfd_host_static_native_qdq_program,tb_hbm_host_static_native_qdq}.sv \
 rtl/hbm_accel/generic/qw/static/{ot_hgi_qdq_host_static,ot_hgi_qdq_record_calendar}.sv \
 rtl/hbm_accel/generic/vm/static/{ot_static_program_target,ot_vms_calendar_static}.sv \
 physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v > "$out/build.log" 2>&1
"$out/obj/sim" +ROWS="$rows" > "$out/run.log" 2>&1
cat "$out/run.log"
grep -q '^HBM_HOST_STATIC_NATIVE_QDQ_PASS' "$out/run.log"
