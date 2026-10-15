#!/usr/bin/env bash
# Run through ot-run with explicit memory/threads. These are component proofs,
# not production schedule, native phase, routed view or whole-token release.
set -euo pipefail
ulimit -c 0
kind=${1:?landing|controller|cdc}; out=${2:?output directory}; shift 2
root=$(cd "$(dirname "$0")/../.." && pwd)
cd "$root"
mkdir -p "$out"
base=rtl/qwen_sys/static_kv_20261014
src=(); negative=3
case "$kind" in
 landing)
  top=tb_static_landing;negative=4
  src=("$base/qkd_static_kv_landing.sv" physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v);;
 controller)
  top=tb_static_host_controller;negative=4
  src=("$base/ot_qkd_static_emb_cdc.sv" "$base/qkd_static_kv_write_observer.sv" "$base/qkd_ctrl_pc_host_static.sv" "$base/ot_qkd_static_ctrl_pc_emb.sv" "$base/ot_qkd_static_kv_timing.sv"
   rtl/qwen_sys/kv_die_20261009/ot_qkvd_kcmd_tap.sv
   rtl/qwen_sys/emb_hbm_20261008/synth/ot_qfd_emb_pcport.sv rtl/qwen_sys/emb_hbm_20261008/ot_qfd_emb_cdc.sv
   rtl/qwen_sys/q5_20261009/synth/ot_qfd_kv_landing_ecc.sv rtl/qwen_sys/host_20261013/qkd_host_static_pc.sv
   rtl/lib/ot_async_fifo.sv rtl/lib/ot_reset_sync.sv);;
 cdc)
  top=tb_static_return_cdc
  src=("$base/qkd_static_kv_return_cdc.sv" rtl/lib/ot_async_fifo.sv rtl/lib/ot_reset_sync.sv);;
 *) exit 2;;
esac
verilator --binary --timing -Wno-fatal -Wno-TIMESCALEMOD -j "${JOBS:-4}" --top-module "$top" --Mdir "$out/obj" -CFLAGS -O1 "$@" "rtl/test/qwen_static_kv/$top.sv" "${src[@]}" > "$out/build.log" 2>&1
"$out/obj/V$top" > "$out/pass.log" 2>&1
cat "$out/pass.log"
for ((mode=1;mode<=negative;mode++)); do
 set +e
 "$out/obj/V$top" +faultmode="$mode" > "$out/mutant_$mode.log" 2>&1
 rc=$?
 set -e
 echo "$kind mutant=$mode exit=$rc"
 if test "$rc" = 0; then exit 1; fi
done
