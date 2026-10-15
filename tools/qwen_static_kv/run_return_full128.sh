#!/usr/bin/env bash
# Separate PROFILE1 discovery creates a frozen compiler fixture. Only PROFILE0
# consumes it during the 128-controller production-mechanism replay.
set -euo pipefail
ulimit -c 0
root=$(cd "$(dirname "$0")/../.." && pwd)
out=${1:?fresh output directory};mkdir -p "$out/source" "$out/fixtures";src="$out/source"
for p in rtl/qwen_sys/static_kv_20261014/{ot_qkd_static_emb_cdc,qkd_static_kv_write_observer,qkd_ctrl_pc_host_static,ot_qkd_static_ctrl_pc_emb,ot_qkd_static_kv_timing}.sv rtl/qwen_sys/kv_die_20261009/ot_qkvd_kcmd_tap.sv rtl/qwen_sys/emb_hbm_20261008/synth/ot_qfd_emb_pcport.sv rtl/qwen_sys/emb_hbm_20261008/ot_qfd_emb_cdc.sv rtl/qwen_sys/q5_20261009/synth/ot_qfd_kv_landing_ecc.sv rtl/qwen_sys/host_20261013/qkd_host_static_pc.sv rtl/lib/{ot_async_fifo,ot_reset_sync}.sv;do
 mkdir -p "$src/$(dirname "$p")";git -C "$root" show "3221e4f5e:$p" > "$src/$p"
done
for p in rtl/qwen_sys/static_kv_20261014/qkd_static_kv_return_slots.sv rtl/qwen_sys/static_kv_20261014/qkd_static_kv_return_calendar.sv;do
 mkdir -p "$src/$(dirname "$p")";git -C "$root" show "8539ea1ef:$p" > "$src/$p"
done
p=rtl/test/qwen_static_kv/tb_static_return_full128.sv;mkdir -p "$src/$(dirname "$p")";cp "$root/$p" "$src/$p"
mapfile -d '' sources < <(find "$src" -name '*.sv' -print0)
for discover in 1 0;do
 verilator --binary --timing -Wno-fatal -j "${JOBS:-4}" --top-module tb_static_return_full128 -GDISCOVERY="$discover" --Mdir "$out/obj$discover" "${sources[@]}" > "$out/build$discover.log" 2>&1
 if ((discover));then
  "$out/obj1/Vtb_static_return_full128" +fixtures="$out/fixtures" > "$out/discovery.log" 2>&1
  find "$out/fixtures" -type f -print0 | sort -z | xargs -0 sha256sum > "$out/fixtures.sha256"
 else
  for phase in 137 637;do
   for mode in 0 1 2 3 4 5 6 7;do
    if "$out/obj0/Vtb_static_return_full128" +fixtures="$out/fixtures" +phase="$phase" +faultmode="$mode" > "$out/p${phase}_m${mode}.log" 2>&1;then rc=0;else rc=$?;fi
    echo "$rc" > "$out/p${phase}_m${mode}.exit"
    if ((mode==0));then test "$rc" = 0;grep -q '^PASS full128 persistent' "$out/p${phase}_m${mode}.log";else test "$rc" != 0;fi
   done
  done
 fi
done
find "$src" -name '*.sv' -print0 | sort -z | xargs -0 sha256sum > "$out/source.sha256"
echo 'PASS full128 actual persistent controllers and frozen independent return calendars; dual phases and seven mutants each'
