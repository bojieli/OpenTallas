#!/bin/bash
set -euo pipefail
out=$1; mut=${2:-0}; shift 2;mkdir -p "$out"
VER=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
b=rtl/hbm_accel/tu/lk_ep_20261010
"$VER" -Irtl/common --binary --timing -O2 -j 4 -Wno-fatal -Wno-lint -Wno-style --top-module tb_hfd_lk_ep_shared -GMUT_RX_SHARED="$mut" --Mdir "$out/obj" -o sim \
 rtl/common/ot_secded.sv rtl/common/ot_secded_dec_dp.sv \
 physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v \
 rtl/hbm_accel/tu/link_retry_sram_20261008/ot_hbm_replay_sram_dp.sv \
 rtl/hbm_accel/tu/link_retry_pipeline_20261009/ot_hbm_link_retry_pipeline_cl.sv \
 rtl/dsrom_sys/s81_ph/ot_s81ph_link_gbx.sv "$b/ot_crc_par.sv" "$b/ot_hbm_lk_ep.sv" "$b/ot_lkep_sub.sv" \
 "$b/ot_lkep_ctrl_phy.sv" "$b/ot_lkep_rx_shared.sv" "$b/ot_lkep_tx_shared.sv" "$b/ot_hbm_lk_ep_shared_golden.sv" "$b/tb_hfd_lk_ep_shared.sv" > "$out/build.log" 2>&1
set +e
"$out/obj/sim" "$@" > "$out/run.log" 2>&1
rc=$?
set -e
cat "$out/run.log"
exit "$rc"
