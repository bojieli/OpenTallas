#!/usr/bin/env bash
# Source-pinned actual persistent controller + independent HBM return calendar
# and fixed dual-clock return slots. Discovery/replay remains a component
# fixture, not a full production command/calendar or physical phase receipt.
set -euo pipefail
ulimit -c 0
root=$(cd "$(dirname "$0")/../.." && pwd)
out=${1:?fresh output directory};mkdir -p "$out/source";src="$out/source"
for p in rtl/qwen_sys/static_kv_20261014/{ot_qkd_static_emb_cdc,qkd_static_kv_write_observer,qkd_ctrl_pc_host_static,ot_qkd_static_ctrl_pc_emb,ot_qkd_static_kv_timing}.sv rtl/qwen_sys/kv_die_20261009/ot_qkvd_kcmd_tap.sv rtl/qwen_sys/emb_hbm_20261008/synth/ot_qfd_emb_pcport.sv rtl/qwen_sys/emb_hbm_20261008/ot_qfd_emb_cdc.sv rtl/qwen_sys/q5_20261009/synth/ot_qfd_kv_landing_ecc.sv rtl/qwen_sys/host_20261013/qkd_host_static_pc.sv rtl/lib/{ot_async_fifo,ot_reset_sync}.sv;do
 mkdir -p "$src/$(dirname "$p")";git -C "$root" show "3221e4f5e:$p" > "$src/$p"
done
p=rtl/qwen_sys/static_kv_20261014/qkd_static_kv_return_slots.sv
mkdir -p "$src/$(dirname "$p")";git -C "$root" show "df5c31ed0:$p" > "$src/$p"
for p in rtl/qwen_sys/static_kv_20261014/qkd_static_kv_return_calendar.sv rtl/test/qwen_static_kv/tb_static_return_controller_calendar.sv;do
 mkdir -p "$src/$(dirname "$p")";cp "$root/$p" "$src/$p"
done
mapfile -d '' sources < <(find "$src" -name '*.sv' -print0)
verilator --binary --timing -Wno-fatal -j "${JOBS:-4}" --top-module tb_static_return_controller_calendar --Mdir "$out/obj" "${sources[@]}" > "$out/build.log" 2>&1
for phase in 137 637;do
 for mode in 0 1 2 3 4 5 6 7;do
  if "$out/obj/Vtb_static_return_controller_calendar" +phase="$phase" +faultmode="$mode" > "$out/p${phase}_m${mode}.log" 2>&1;then rc=0;else rc=$?;fi
  echo "$rc" > "$out/p${phase}_m${mode}.exit"
  if ((mode==0));then test "$rc" = 0;grep -q '^PASS sourcebound' "$out/p${phase}_m${mode}.log";else test "$rc" != 0;fi
 done
done
find "$src" -name '*.sv' -print0 | sort -z | xargs -0 sha256sum > "$out/source.sha256"
echo 'PASS two phases actual controller K256/V256, independent RD-to-co32 predictor, 512 dual-clock sectors each; seven faults rejected per phase'
