#!/bin/bash
# Component ABI gate; TREE is the captured native source tree, OUT is an owned scratch directory.
set -euo pipefail
TREE=$(readlink -f "$1"); OUT=$(mkdir -p "$2" && readlink -f "$2")
H=$(cd "$(dirname "$0")" && pwd); ROOT=$(cd "$H/../../.." && pwd)
mkdir -p "$OUT/src" "$OUT/mu" "$OUT/ages"
python3 "$ROOT/tools/qwen_layerbench/kv_dieslice/native_boot_ages.py" dispatch "$TREE/rtl/qwen_sys/static_kv_die_20261017/qkd_kv_ctl_nc32_face.sv" "$OUT/src/dispatch.sv"
SRC=("$OUT/src/dispatch.sv" "$TREE/rtl/qwen_sys/static_kv_die_20261017/qkd_kv_ctl_c32_boot.sv" "$TREE/rtl/lib/ot_s32_cells.sv")
cp "$H/target1_su.hex" "$OUT/mu/target1.hex"
cp "$H/target1_mu.hex" "$OUT/mu/target1_mu.hex"
(cd "$OUT/mu"; verilator --binary --timing -Wno-fatal -j 4 --top-module tb -Mdir obj -o sim "$H/tb_boot_mu_abi_positive.sv" "${SRC[@]}" > build.log 2>&1; ./obj/sim > run.log 2>&1)
cp "$H/target10.hex" "$OUT/ages/target10.hex"
(cd "$OUT/ages"; verilator --binary --timing -Wno-fatal -j 4 --top-module tb -Mdir obj -o sim "$H/tb_boot_age_miter.sv" "$H/legacy_dispatch.sv" "${SRC[@]}" "$TREE/rtl/qwen_sys/static_kv_die_20261017/qkd_kv_ctl_c32_dcfg.sv" "$TREE/rtl/qwen_sys/static_kv_die_20261017/qkd_kv_ctl_c32_misc.sv" > build.log 2>&1; ./obj/sim > run.log 2>&1)
grep PASS "$OUT/mu/run.log" "$OUT/ages/run.log"
