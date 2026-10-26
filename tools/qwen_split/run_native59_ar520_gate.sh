#!/usr/bin/env bash
set -euo pipefail
root=$(cd "$(dirname "$0")/../.." && pwd);out=${1:?fresh outputdirectory};mkdir "$out"
for mode in positive stale_result missing_commit missing_visibility remote_writer_fault invalid_vm_address native_route_unqualified stale_metadata_guard_mutant return_register_bypass;do
 p=();case "$mode" in return_register_bypass)p=(-DQFD_NATIVE_RET_MUT_BYPASS);;invalid_vm_address)p=(-Ptb_qfd_native59_ar520_component.BAD_ADDRESS=1);;remote_writer_fault)p=(-Ptb_qfd_native59_ar520_component.BAD_STATUS=1);;native_route_unqualified)p=(-Ptb_qfd_native59_ar520_component.NATIVE_PROFILE=1);;missing_visibility)p=(-Ptb_qfd_native59_ar520_component.NO_VISIBILITY=1);;missing_commit)p=(-Ptb_qfd_native59_ar520_component.BAD_COMMIT=1);;stale_result)p=(-Ptb_qfd_native59_ar520_component.BAD_RESULT=1);;stale_metadata_guard_mutant)p=(-Ptb_qfd_native59_ar520_component.BAD_RESULT=1 -Ptb_qfd_native59_ar520_component.CODEC_MUT=2);;esac
 iverilog -g2012 -s tb_qfd_native59_ar520_component "${p[@]}" -o "$out/$mode.sim" \
 "$root/rtl/qwen_split/qfd_native59_q_export_control.sv" "$root/rtl/qwen_split/qfd_native59_compute_service.sv" "$root/rtl/qwen_split/qfd_native59_command_context.sv" \
 "$root/rtl/qwen_split/qfd_native59_static_service.sv" "$root/rtl/qwen_split/qfd_native59_record_endpoint.sv" \
 "$root/rtl/qwen_split/qfd_kvn_static_transport.sv" "$root/rtl/qwen_sys/redesign_qwen/ot_qfd_su_kv_static_posted.sv" \
 "$root/rtl/qwen_sys/vm_nox_20261014/qfd_vm_attention_commit_fence.sv" "$root/rtl/qwen_sys/split_20261014/qkd_native_attention_record.sv" "$root/rtl/test/qwen_split/tb_qfd_native59_ar520_component.sv" > "$out/$mode.compile.log" 2>&1
 if vvp "$out/$mode.sim" > "$out/$mode.log" 2>&1;then rc=0;else rc=$?;fi
 echo "$rc" > "$out/$mode.exit"
 if [[ "$mode" == return_register_bypass ]];then [[ "$rc" != 0 ]];grep -q "FAIL native_ret registered observation edge" "$out/$mode.log";elif [[ "$mode" == native_route_unqualified ]];then [[ "$rc" != 0 ]];grep -q "requires measured VM" "$out/$mode.log";elif [[ "$mode" == stale_metadata_guard_mutant ]];then [[ "$rc" != 0 ]];grep -q '^FATAL:.*FAIL stale remote metadata' "$out/$mode.log";else [[ "$rc" == 0 ]];grep -q '^PASS selected local native service' "$out/$mode.log";fi
 cat "$out/$mode.log";rm "$out/$mode.sim"
done
sha256sum "$root/rtl/qwen_split/qfd_native59_q_export_control.sv" "$root/rtl/qwen_split/qfd_native59_compute_service.sv" "$root/rtl/qwen_split/qfd_native59_command_context.sv" "$root/rtl/qwen_split/qfd_native59_static_service.sv" "$root/rtl/qwen_split/qfd_native59_record_endpoint.sv" "$root/rtl/qwen_split/qfd_kvn_static_transport.sv" "$root/rtl/qwen_sys/redesign_qwen/ot_qfd_su_kv_static_posted.sv" "$root/rtl/qwen_sys/vm_nox_20261014/qfd_vm_attention_commit_fence.sv" "$root/rtl/qwen_sys/split_20261014/qkd_native_attention_record.sv" "$root/rtl/test/qwen_split/tb_qfd_native59_ar520_component.sv" > "$out/source.sha256"
