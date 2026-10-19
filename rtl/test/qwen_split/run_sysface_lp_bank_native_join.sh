#!/bin/bash
# Fleet component probe. Pass source-root containing exact c11 CTLM sources + packet.
set -eu
OUT=$(realpath -m "$1");S=$(realpath "$2");R=$(cd "$(dirname "$0")/../../.." && pwd);mkdir -p "$OUT"
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
"$V" --version > "$OUT/verilator.txt";grep -q 5.050 "$OUT/verilator.txt"
P="$S/results/rtl/mu_qwen_1018/admission/F16_P2"
for m in ${LP_MUTANTS:-0 5 6 7 8 9 10};do
 "$V" --binary --timing -j 4 -O2 -Wno-fatal -Wno-lint -Wno-style -Wno-WIDTH --top-module tb_sysface_lp_bank_native_join -GMUT=$m -GCAPTURE2=${LP_CAPTURE2:-0} --Mdir "$OUT/obj$m" \
 "$R/rtl/qwen_sys/mu_embedding_20261019/qfd_embedding_identity_capture_model.sv" "$S/rtl/qwen_sys/mu_embedding_20261019/qfd_embedding_validation_arm.sv" "$S/rtl/qwen_split/qfd_embedding_word_provider.sv" "$S/rtl/qwen_sys/static_embedding_20261014/qkd_embedding_static_preload_face.sv" "$S/rtl/qwen_sys/static_embedding_20261014/qkd_embedding_static_core_store.sv" "$S/results/rtl/qwen_mu_embedding_contract_1019/validation_arm/safe2_sources/rtl/qwen_split/qfd_native59_dv_service.sv" "$S/results/rtl/qwen_mu_embedding_contract_1019/validation_arm/safe2_sources/rtl/qwen_split/qfd_native59_q_export_control.sv" "$S/results/rtl/qwen_mu_embedding_contract_1019/validation_arm/safe2_sources/rtl/qwen_split/qfd_native59_command_context.sv" "$S/results/rtl/qwen_mu_embedding_contract_1019/validation_arm/safe2_sources/rtl/qwen_split/qfd_native59_static_service.sv" "$S/results/rtl/qwen_mu_embedding_contract_1019/validation_arm/safe2_sources/rtl/qwen_split/qfd_native59_record_endpoint.sv" "$S/results/rtl/qwen_mu_embedding_contract_1019/validation_arm/safe2_sources/rtl/qwen_split/qfd_kvn_static_transport.sv" "$S/results/rtl/qwen_mu_embedding_contract_1019/validation_arm/safe2_sources/rtl/qwen_sys/redesign_qwen/ot_qfd_su_kv_static_posted.sv" "$S/results/rtl/qwen_mu_embedding_contract_1019/validation_arm/safe2_sources/rtl/qwen_sys/vm_nox_20261014/qfd_vm_attention_commit_fence.sv" "$S/results/rtl/qwen_mu_embedding_contract_1019/validation_arm/safe2_sources/rtl/qwen_sys/split_20261014/qkd_native_attention_record.sv" "$S/results/rtl/qwen_mu_embedding_contract_1019/validation_arm/safe2_sources/rtl/qwen_split/qfd_native59_qseat_sram.sv" "$S/results/rtl/qwen_mu_embedding_contract_1019/validation_arm/safe2_sources/physical/asap7_memory_macros/ot_sram_1r1w_32x512_m1/ot_sram_1r1w_32x512_m1.v" \
 "$S/rtl/common/landed_parent/ot_pl_land.sv" \
 "$S/physical/asap7_memory_macros/ot_rom_4096x72_m8/ot_rom_4096x72_m8.v" "$S/physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v" \
 "$R/rtl/qwen_sys/context_transport_20261014/qkd_context_records.sv" "$R/rtl/qwen_split/qfd_sys_face_accepted_mu_identity.sv" "$R/rtl/qwen_sys/mu_embedding_20261019/qfd_mu_embedding_cold_epoch_model.sv" \
 "$S/rtl/qwen_sys/program_receiver_20261014/qkd_program_commit.sv" "$S/rtl/qwen_dv/qfd_mu_context_guard.sv" "$S/rtl/qwen_split/mu/qfd_sys_face_mu_dhuser.sv" "$S/rtl/qwen_dv/qfd_dv_cmd_cal_mu.sv" "$S/rtl/qwen_dv/qfd_tt_ctlm_dv_lpf_parts.sv" "$R/rtl/test/qwen_split/tb_sysface_lp_bank_native_join.sv" > "$OUT/build$m.log" 2>&1
 if [ "$m" = 0 ];then tokens="0 65536 151935";else tokens="65536";fi
 for tok in $tokens;do
  set +e;"$OUT/obj$m/Vtb_sysface_lp_bank_native_join" +OT_ROM_DIR="$P" +PACKET="$P" +TOKEN="$tok" +VECTORS="$S/results/arch/qwen_tp8_native_dispatch_1014/embedding_vectors/token$tok" > "$OUT/run${m}_$tok.log" 2>&1;rc=$?;set -e
  cat "$OUT/run${m}_$tok.log"
  if [ "$m" = 0 ];then test "$rc" = 0;grep -q LP_NATIVE_PASS "$OUT/run${m}_$tok.log";else test "$rc" != 0;grep -q LP_NATIVE_FAIL "$OUT/run${m}_$tok.log";fi
 done
done
