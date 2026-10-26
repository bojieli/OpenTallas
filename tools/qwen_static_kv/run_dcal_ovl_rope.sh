#!/bin/bash
# Run one exactness/negative-control case; retain binary and immutable witness log.
set -eu
OUT=$(realpath -m "$1")
MODE=${2:-0}
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
D=rtl/qwen_sys/d2d_static_20261015
DMUT=0
HMUT=0
if [ "$MODE" = 6 ]; then HMUT=1; fi
if [ "$MODE" = 1 ]; then DMUT=1; fi
KEY=$(sha256sum "$0" "$D/ot_qwen_d2d_cal_seq.sv" "$D/ot_qwen_d2d_ovl_seq.sv"   "$D/qkd_d2d_cal_seq_ovl_rope.sv" rtl/test/qwen_split/tb_kv_dcal_ovl_rope.sv   "$D/ovl_release_rope/ovl_release_img.svh" "$D/ovl_release_rope/ovl_wrapper_params.svh" "$D"/ovl_release_rope/ovl_k_*.viamap.hex   physical/asap7_memory_macros/ot_rom_4096x72_m8/ot_rom_4096x72_m8.v | sha256sum | cut -c1-12)
OBJ="$OUT/obj_m${DMUT}_h${HMUT}_${KEY}"
mkdir -p "$OUT"
"$V" --version > "$OUT/verilator.txt"
if [ ! -x "$OBJ/Vtb_kv_dcal_ovl_rope" ]; then
  "$V" --binary --timing -j "${JOBS:-4}" -O2 -Wno-fatal -Wno-lint -Wno-style -Wno-WIDTH \
    -I"$D" --top-module tb_kv_dcal_ovl_rope -GDMUT="$DMUT" -GHMUT="$HMUT" --Mdir "$OBJ" \
    physical/asap7_memory_macros/ot_rom_4096x72_m8/ot_rom_4096x72_m8.v \
    "$D/ot_qwen_d2d_cal_seq.sv" "$D/ot_qwen_d2d_ovl_seq.sv" \
    "$D/qkd_d2d_cal_seq_ovl_rope.sv" rtl/test/qwen_split/tb_kv_dcal_ovl_rope.sv \
    > "$OUT/build_m${DMUT}.log" 2>&1
fi
set +e
"$OBJ/Vtb_kv_dcal_ovl_rope" +MUT="$MODE" > "$OUT/run_m${MODE}.log" 2>&1
rc=$?
set -e
cat "$OUT/run_m${MODE}.log"
exit "$rc"
