#!/usr/bin/env bash
set -euo pipefail
root=$(cd "$(dirname "$0")/../.." && pwd)
out=${1:?fresh output directory};mkdir -p "$out"
for phase in 0.137 0.637;do
 obj="$out/obj-$phase"
 verilator --binary --timing -j 2 -Wno-fatal --top-module tb_static_return_slots -GCORE_PHASE="$phase" -GDEPTH="${DEPTH:-8}" --Mdir "$obj" "$root/rtl/qwen_sys/static_kv_20261014/qkd_static_kv_return_slots.sv" "$root/rtl/test/qwen_static_kv/tb_static_return_slots.sv" > "$out/build-$phase.log" 2>&1
 for mode in 0 1 2 3;do
  if "$obj/Vtb_static_return_slots" +faultmode="$mode" > "$out/phase$phase-mode$mode.log" 2>&1;then rc=0;else rc=$?;fi
  echo "$rc" > "$out/phase$phase-mode$mode.exit"
  if [[ "$mode" == 0 ]];then [[ "$rc" == 0 ]];grep -q '^PASS native return slots' "$out/phase$phase-mode$mode.log"
  else [[ "$rc" != 0 ]];grep -q '^FAIL native return slots' "$out/phase$phase-mode$mode.log";fi
  cat "$out/phase$phase-mode$mode.log"
 done
done
verilator --binary --timing -j 2 -Wno-fatal +define+OT_KV_RETURN_MUT_READ_ADDR -GDEPTH="${DEPTH:-8}" --top-module tb_static_return_slots --Mdir "$out/obj-mutant" "$root/rtl/qwen_sys/static_kv_20261014/qkd_static_kv_return_slots.sv" "$root/rtl/test/qwen_static_kv/tb_static_return_slots.sv" > "$out/build-mutant.log" 2>&1
if "$out/obj-mutant/Vtb_static_return_slots" > "$out/read-address-mutant.log" 2>&1;then rc=0;else rc=$?;fi
echo "$rc" > "$out/read-address-mutant.exit"
[[ "$rc" != 0 ]];grep -q '^FAIL native return slots' "$out/read-address-mutant.log"
cat "$out/read-address-mutant.log"
sha256sum "$root/rtl/qwen_sys/static_kv_20261014/qkd_static_kv_return_slots.sv" "$root/rtl/test/qwen_static_kv/tb_static_return_slots.sv" > "$out/source.sha256"
