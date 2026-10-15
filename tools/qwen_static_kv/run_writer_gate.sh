#!/usr/bin/env bash
set -euo pipefail
root=$(cd "$(dirname "$0")/../.." && pwd)
out=${1:?fresh output directory};mkdir "$out"
src="$out/source";mkdir "$src"
if [[ -n "${WRITER_SOURCE:-}" ]];then cp -r "$WRITER_SOURCE/." "$src/";else
for p in rtl/qwen_split/{qfd_native59_compute_service,qfd_native59_command_context,qfd_native59_static_service,qfd_native59_record_endpoint,qfd_kvn_static_transport}.sv rtl/qwen_sys/redesign_qwen/ot_qfd_su_kv_static_posted.sv;do
 mkdir -p "$src/$(dirname "$p")";git -C "$root" show "970b75b99:$p" > "$src/$p"
done
for spec in fe242d5ba:rtl/qwen_sys/vm_nox_20261014/qfd_vm_attention_commit_fence.sv 34cfa0d07:rtl/qwen_sys/split_20261014/qkd_native_attention_record.sv;do
 p=${spec#*:};mkdir -p "$src/$(dirname "$p")";git -C "$root" show "$spec" > "$src/$p"
done
cp "$root/rtl/qwen_sys/static_kv_20261014/qkd_kv_static_writer.sv" "$src/"
cp "$root/rtl/test/qwen_static_kv/"*.sv "$src/"
fi
for top in tb_qkd_kv_static_writer tb_qkd_kv_static_composed;do
 for mode in 0 1 2 3 4 5 6;do
  p=(-P"$top.MUT=$mode")
  iverilog -g2012 -s "$top" "${p[@]}" -o "$out/$top-$mode.sim" "$src/qkd_kv_static_writer.sv" "$src/$top.sv" "$src"/rtl/qwen_split/*.sv "$src"/rtl/qwen_sys/*/*.sv > "$out/$top-$mode.compile.log" 2>&1
  if vvp "$out/$top-$mode.sim" > "$out/$top-$mode.log" 2>&1;then rc=0;else rc=$?;fi
  echo "$rc" > "$out/$top-$mode.exit"
  if [[ "$top" == tb_qkd_kv_static_composed && "$mode" != 0 ]];then
   [[ $rc != 0 ]];grep -q '^FATAL:.*FAIL' "$out/$top-$mode.log"
  else
   [[ $rc == 0 ]];if [[ $mode == 0 ]];then grep -q '^PASS' "$out/$top-$mode.log";else grep -q '^OBSERVED_FAIL' "$out/$top-$mode.log";fi
  fi
  cat "$out/$top-$mode.log";rm "$out/$top-$mode.sim"
 done
done
for bad in 1 2;do
 top=tb_qkd_kv_static_writer
 iverilog -g2012 -s "$top" -P"$top.BAD=$bad" -o "$out/bad-$bad.sim" "$src/qkd_kv_static_writer.sv" "$src/$top.sv"
 vvp "$out/bad-$bad.sim" > "$out/bad-$bad.log";grep -q '^OBSERVED_FAIL' "$out/bad-$bad.log";cat "$out/bad-$bad.log";rm "$out/bad-$bad.sim"
done
find "$src" -name '*.sv' -type f -print0 | sort -z | xargs -0 sha256sum > "$out/source.sha256"
