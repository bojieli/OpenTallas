#!/bin/bash
# TOKSIM-KVATTN 2026-10-19: build the release KV-die attention vehicle (tb_kvattn_rel), Verilator 5.050 hierarchical.
# Usage: build.sh SRC_ROOT OUT_DIR    (SRC_ROOT = checkout of the measured commit)
set -euo pipefail
R=$(realpath "$1"); O=$(realpath -m "$2"); mkdir -p "$O"
vl=${VL:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
cd "$R"
python3 tools/qwen_attention_native/gen_astk_cal.py --check > "$O/gen_check.log"
python3 tools/qwen_attention_native/gen_pv_rate.py --check >> "$O/gen_check.log"
mapfile -t SRC < tools/qwen_layerbench/kvattn_rel/sources.txt
sha256sum "${SRC[@]}" tools/qwen_layerbench/kvattn_rel/kvattn_rel.vlt tools/qwen_layerbench/kvattn_rel/build.sh > "$O/source.sha256"
"$vl" --version > "$O/verilator.version"
s=$(date +%s)
/usr/bin/time -v -o "$O/build.time" "$vl" --binary --timing --hierarchical -j "${VJOBS:-16}" --build-jobs "${JOBS:-32}" -O2 \
  -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN -Wno-WIDTH -Wno-SELRANGE \
  +define+KVD_HEADS=1 +define+KVD_Q_FP32=1 +define+KVD_QK_ONLY=1 --top-module tb_kvattn_rel --Mdir "$O/obj" \
  tools/qwen_layerbench/kvattn_rel/kvattn_rel.vlt "${SRC[@]}" > "$O/build.log" 2>&1
echo "build_seconds $(( $(date +%s) - s ))" >> "$O/build.log"
sha256sum "$O/obj/Vtb_kvattn_rel" > "$O/binary.sha256"
echo BUILD_OK
