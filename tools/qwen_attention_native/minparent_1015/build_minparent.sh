#!/bin/bash
set -euo pipefail
stage=$(cd "$(dirname "$0")" && pwd)
archive_root=${QATTN_ARCHIVE_ROOT:?set QATTN_ARCHIVE_ROOT to copied immutable b4 obj libraries}
vl=${VL:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
out=${1:-$stage/build}
mkdir -p "$out"
libs=(); while IFS= read -r f; do libs+=("$f"); done < <(find "$archive_root" -mindepth 2 -maxdepth 2 -name 'lib*.a' | sort)
[[ ${#libs[@]} == 33 ]]
(cd "$archive_root" && sha256sum -c "$stage/b4-artifacts.sha256") > "$out/artifacts_check.log"
link="-Wl,--start-group ${libs[*]} -Wl,--end-group"
/usr/bin/time -v "$vl" --binary --timing -O2 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN -Wno-WIDTH --build-jobs 16 --top-module tb_qwen_tp8_attention_native_service --Mdir "$out/obj" -LDFLAGS "$link" \
 "$stage/stubs/Vot_qwen_tp8_attention_native_stack_cp_c/ot_qwen_tp8_attention_native_stack_cp_c.sv" \
 "$stage/stubs/Vot_qwen_tp8_pv256_pair_c/ot_qwen_tp8_pv256_pair_c.sv" \
 "$stage/stubs/Vot_qwen_tp8_pv256_pair_b/ot_qwen_tp8_pv256_pair_b.sv" \
 "$stage/stubs/Vot_qkd_ahub_static_die_cal_3/ot_qkd_ahub_static_die_cal_3.sv" \
 "$stage/stubs/Vot_qwen_tp8_pv256_finalize_static_cal_8/ot_qwen_tp8_pv256_finalize_static_cal_8.sv" \
 "$stage/qattn_minparent_pair.sv" "$stage/ot_qwen_tp8_vrow_static.sv" "$stage/ot_qwen_tp8_vrow_capture.sv" \
 "$stage/ot_qwen_tp8_attention_native_service.sv" "$stage/tb_qwen_tp8_attention_native_service.sv" > "$out/build.log" 2>&1
sha256sum "$out/obj/Vtb_qwen_tp8_attention_native_service" > "$out/binary.sha256"
