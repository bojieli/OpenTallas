#!/bin/bash
# Selector-only legal component programme: public production image/absolute epoch remain unbound.
set -eu
OUT=$(realpath -m "$1");R=$(cd "$(dirname "$0")/../../.." && pwd)
DSEQ=ot_qwen_d2d_cal_seq_dies_mu.sv
mkdir -p "$OUT/img"
python3 "$R/rtl/test/qwen_split/build_sysface_cold_fixture.py" "$R" "$OUT/img" "${MUT:-0}"
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
"$V" --version > "$OUT/verilator.txt";grep -q 5.050 "$OUT/verilator.txt"
"$V" --binary --timing -j 4 -O2 -Wno-fatal -Wno-lint -Wno-style -Wno-WIDTH -I"$OUT" -I"$R/rtl/qwen_sys/d2d_static_20261015" --top-module tb_qfd_sys_face_cold -GMU=1 -GMUT=${MUT:-0} -GSRAM_CAL=${SRAM_CAL:-0} -GIMG=\"$OUT/img\" --Mdir "$OUT/obj" \
 "$R/rtl/qwen_sys/d2d_static_20261015/ot_qwen_d2d_cal_sram.sv" "$R/physical/asap7_memory_macros/ot_sram_1r1w_64x16_m1/ot_sram_1r1w_64x16_m1.v" \
 "$R/rtl/qwen_split/qfd_sys_face.sv" "$R/rtl/qwen_split/qfd_embedding_word_provider.sv" \
 "$R/rtl/qwen_split/qfd_sys_face_accepted_mu_ctx.sv" \
 "$R/rtl/qwen_sys/d2d_static_20261015/ot_qwen_d2d_static.sv" \
 "$R/rtl/qwen_sys/d2d_static_20261015/ot_qwen_d2d_ovl_seq.sv" "$R/rtl/qwen_sys/d2d_static_20261015/qfd_d2d_cal_seq_ovl.sv" \
 "$R/rtl/qwen_sys/d2d_static_20261015/ot_qwen_d2d_cal_seq.sv" "$R/rtl/qwen_sys/d2d_static_20261015/$DSEQ" \
 "$R/rtl/qwen_split/qfd_sys_face_record_port.sv" \
 "$R/rtl/qwen_sys/context_transport_20261014/qkd_context_records.sv" \
 "$R/rtl/qwen_sys/program_receiver_20261014/qkd_program_commit.sv" \
 "$R/rtl/qwen_sys/static_embedding_20261014/qkd_embedding_static_preload_face.sv" \
 "$R/rtl/qwen_sys/static_embedding_20261014/qkd_embedding_static_core_store.sv" \
 "$R/physical/asap7_memory_macros/ot_rom_4096x72_m8/ot_rom_4096x72_m8.v" \
 "$R/physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v" \
 "$R/rtl/test/qwen_split/tb_qfd_sys_face_cold.sv" > "$OUT/build.log" 2>&1
set +e
"$OUT/obj/Vtb_qfd_sys_face_cold" > "$OUT/run.log" 2>&1
rc=$?
set -e
cat "$OUT/run.log"
if [ "${MUT:-0}" = 0 ]; then test "$rc" = 0; grep -q SYS_FACE_COLD_PASS "$OUT/run.log"; else test "$rc" != 0; grep -q SYS_FACE_COLD_FAIL "$OUT/run.log"; fi
