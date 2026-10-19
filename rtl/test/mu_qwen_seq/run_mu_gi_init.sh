#!/bin/bash
# Fleet only. Actual public class-calendar image; arithmetic returns scripted.
set -euo pipefail
D=$(cd "$(dirname "$0")" && pwd); R=$(cd "$D/../../.." && pwd)
W=${1:?work}; P=${2:?packet}; mkdir -p "$W";W=$(cd "$W" && pwd)
python3 "$D/gi_init_fixture.py" "$P" "$W"
VL=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
build() {
"$VL" --binary --timing -j 8 -Wno-fatal -Wno-lint -Wno-style --top-module tb_mu_gi_init -GBAD_COUNT="$1" -Mdir "$W/obj$1" -o sim \
 "$R/physical/asap7_memory_macros/ot_rom_4096x72_m8/ot_rom_4096x72_m8.v" \
 "$R/physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v" \
 "$R/rtl/qwen_sys/context_transport_20261014/qkd_context_records.sv" "$R/rtl/qwen_split/qfd_sys_face_accepted_mu_ctx.sv" \
 "$R/rtl/qwen_sys/program_receiver_20261014/qkd_program_commit.sv" "$R/rtl/qwen_dv/qfd_mu_context_guard.sv" \
 "$R/rtl/qwen_split/mu/qfd_sys_face_mu_dhuser.sv" "$R/rtl/qwen_dv/qfd_dv_cmd_cal_mu.sv" \
 "$R/rtl/qwen_dv/qfd_tt_ctlm_dv_lpf_parts.sv" "$D/tb_mu_gi_init.sv" >"$W/build$1.log" 2>&1
}
build 0
for MUT in ${GI_MUTANTS:-0 1 2 3};do
 "$W/obj0/sim" +OT_ROM_DIR="$P" +PACKET="$P" +EVENTS="$W/events.txt" +LIMITS="$W/limits.txt" +MUT="$MUT" >"$W/mut$MUT.log" 2>&1
 cat "$W/mut$MUT.log"
 if [ "$MUT" = 0 ];then grep -q '^TB_MU_GI_INIT PASS' "$W/mut$MUT.log";else grep -q '^TB_MU_GI_INIT FAIL' "$W/mut$MUT.log";fi
done
# Reject the concrete count1024 truncation case before any stimulus.
build 1
set +e
"$W/obj1/sim" +OT_ROM_DIR="$P" +PACKET="$P" +EVENTS="$W/events.txt" +LIMITS="$W/limits.txt" >"$W/bad_count.log" 2>&1
rc=$?
set -e
[ "$rc" -ne 0 ]
grep -q 'INIT_U0 requires a source-bound aligned INIT_FIRST/INIT_CNT' "$W/bad_count.log"
echo "TB_MU_GI_INIT BAD_COUNT correctly rejected rc=$rc"
