#!/bin/bash
# Fleet component probe. Pass source-root containing exact c11 CTLM sources + packet.
set -eu
OUT=$(realpath -m "$1");S=$(realpath "$2");R=$(cd "$(dirname "$0")/../../.." && pwd);mkdir -p "$OUT"
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
"$V" --version > "$OUT/verilator.txt";grep -q 5.050 "$OUT/verilator.txt"
P="$S/results/rtl/mu_qwen_1018/admission/F16_P2"
for m in ${LP_MUTANTS:-0 1 2 3 4};do
 "$V" --binary --timing -j 4 -O2 -Wno-fatal -Wno-lint -Wno-style -Wno-WIDTH --top-module tb_sysface_lp_bank_join -GMUT=$m --Mdir "$OUT/obj$m" \
 "$S/rtl/common/landed_parent/ot_pl_land.sv" \
 "$S/physical/asap7_memory_macros/ot_rom_4096x72_m8/ot_rom_4096x72_m8.v" "$S/physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v" \
 "$R/rtl/qwen_sys/context_transport_20261014/qkd_context_records.sv" "$R/rtl/qwen_split/qfd_sys_face_accepted_mu_identity.sv" "$R/rtl/qwen_sys/mu_embedding_20261019/qfd_mu_embedding_cold_epoch_model.sv" \
 "$S/rtl/qwen_sys/program_receiver_20261014/qkd_program_commit.sv" "$S/rtl/qwen_dv/qfd_mu_context_guard.sv" "$S/rtl/qwen_split/mu/qfd_sys_face_mu_dhuser.sv" "$S/rtl/qwen_dv/qfd_dv_cmd_cal_mu.sv" "$S/rtl/qwen_dv/qfd_tt_ctlm_dv_lpf_parts.sv" "$R/rtl/test/qwen_split/tb_sysface_lp_bank_join.sv" > "$OUT/build$m.log" 2>&1
 set +e;"$OUT/obj$m/Vtb_sysface_lp_bank_join" +OT_ROM_DIR="$P" +PACKET="$P" > "$OUT/run$m.log" 2>&1;rc=$?;set -e
 cat "$OUT/run$m.log"
 if [ "$m" = 0 ];then test "$rc" = 0;grep -q LP_BANK_PASS "$OUT/run$m.log";else test "$rc" != 0;grep -q LP_BANK_FAIL "$OUT/run$m.log";fi
done
