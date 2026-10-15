#!/usr/bin/env bash
# Four actual physical PCs, immutable source composition; common-clock boundary
# proof only. Full128PC route/relay/phase/calendar qualification is separate.
set -euo pipefail
root=$(cd "$(dirname "$0")/../.." && pwd)
out=${1:?fresh directory};mkdir "$out"
src="$out/source";mkdir "$src"
if [[ -n "${WRITER_PHYSICAL_SOURCE:-}" ]];then cp -r "$WRITER_PHYSICAL_SOURCE/." "$src/";else
 for p in rtl/qwen_split/{qfd_native59_compute_service,qfd_native59_command_context,qfd_native59_static_service,qfd_native59_record_endpoint,qfd_kvn_static_transport}.sv rtl/qwen_sys/redesign_qwen/ot_qfd_su_kv_static_posted.sv;do
  mkdir -p "$src/$(dirname "$p")";git -C "$root" show "970b75b99:$p" > "$src/$p"
 done
 for spec in fe242d5ba:rtl/qwen_sys/vm_nox_20261014/qfd_vm_attention_commit_fence.sv 34cfa0d07:rtl/qwen_sys/split_20261014/qkd_native_attention_record.sv;do
  p=${spec#*:};mkdir -p "$src/$(dirname "$p")";git -C "$root" show "$spec" > "$src/$p"
 done
 for p in rtl/qwen_sys/static_kv_20261014/{ot_qkd_static_emb_cdc,qkd_static_kv_write_observer,qkd_ctrl_pc_host_static,ot_qkd_static_ctrl_pc_emb,ot_qkd_static_kv_timing}.sv rtl/qwen_sys/kv_die_20261009/ot_qkvd_kcmd_tap.sv rtl/qwen_sys/emb_hbm_20261008/synth/ot_qfd_emb_pcport.sv rtl/qwen_sys/q5_20261009/synth/ot_qfd_kv_landing_ecc.sv rtl/qwen_sys/host_20261013/qkd_host_static_pc.sv rtl/lib/{ot_async_fifo,ot_reset_sync}.sv;do
  mkdir -p "$src/$(dirname "$p")";git -C "$root" show "6f673e98d:$p" > "$src/$p"
 done
 cp "$root/rtl/qwen_sys/static_kv_20261014/qkd_kv_static_writer.sv" "$src/"
 cp "$root/rtl/test/qwen_static_kv/tb_qkd_kv_physical_composed.sv" "$src/"
fi
mapfile -d '' sources < <(find "$src" -name '*.sv' -print0)
for mut in 0 1 2 3 4 5 6;do
 top=tb_qkd_kv_physical_composed
 iverilog -g2012 -s "$top" -P"$top.MUT=$mut" -o "$out/$mut.sim" "${sources[@]}" > "$out/$mut.compile.log" 2>&1
 if vvp "$out/$mut.sim" > "$out/$mut.log" 2>&1;then rc=0;else rc=$?;fi
 echo "$rc" > "$out/$mut.exit"
 if [[ "$mut" == 0 ]];then [[ "$rc" == 0 ]];grep -q '^PASS actualformatter' "$out/$mut.log";else [[ "$rc" != 0 ]];grep -q '^FATAL:.*FAIL' "$out/$mut.log";fi
 if [[ "$mut" == 1 ]];then grep -q '^BAD raw physical data' "$out/$mut.log";elif ((mut>=2));then grep -q '^DETECTED_BEFORE_HBM_RETIRE' "$out/$mut.log";fi
 cat "$out/$mut.log";rm "$out/$mut.sim"
done
find "$src" -name '*.sv' -type f -print0 | sort -z | xargs -0 sha256sum > "$out/source.sha256"
