#!/usr/bin/env bash
# usage: run_bmul_gu.sh <outdir> [closed]  -> BMUL_GU PASS (gradual-underflow lanes) / FAIL (closed lanes, negative control)
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/../../../.." && pwd); OUT=$(realpath -m "$1"); MODE=${2:-gu}; mkdir -p "$OUT"; cd "$ROOT"
VL=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
python3 - "$OUT" <<'P'
import sys, numpy as np
out = sys.argv[1]; rng = np.random.default_rng(7); N = 200000
def rb(n, lo, hi):
    return (rng.integers(0, 2, n) << 15) | (rng.integers(lo, hi + 1, n) << 7) | rng.integers(0, 128, n)
a = np.concatenate([rb(N // 2, 0, 140), rb(N // 4, 0, 255), rb(N // 4, 100, 130)])
b = np.concatenate([rb(N // 2, 0, 140), rb(N // 4, 0, 255), rb(N // 4, 0, 20)])
fa = (a.astype(np.uint32) << 16).view(np.float32); fb = (b.astype(np.uint32) << 16).view(np.float32)
with np.errstate(all="ignore"):
    y = (fa * fb).astype(np.float32)
y = np.where(y == 0, np.float32(0), y).view(np.uint32)
bad = (((a >> 7) & 0xFF) == 255) | (((b >> 7) & 0xFF) == 255) | ~np.isfinite(y.view(np.float32))
for n, v, fmt in (("a", a, "%04x"), ("b", b, "%04x"), ("y", y, "%08x"), ("f", bad.astype(int), "%d")):
    np.savetxt(f"{out}/{n}.hex", v, fmt=fmt)
P
DEF=(); [[ $MODE == closed ]] && DEF=(-DBMUL_CLOSED)
"$VL" --binary -O1 -Wno-fatal -Wno-lint -Wno-style -j 8 "${DEF[@]}" --top-module tb_gu --Mdir "$OUT/obj_$MODE" \
  rtl/test/hbm_accel/sm_gu/tb_bmul_gu.sv rtl/hbm_accel/sm/ot_hbm_accel_smh_gu.sv rtl/hbm_accel/sm/ot_hbm_accel_smh_bd.sv \
  rtl/hdc/ot_hdc_prefix.sv rtl/gpu/ot_gpu_fadd.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_fastfp.sv \
  rtl/hdc/ot_hdc_fpu.sv rtl/hdc/ot_hdc_sfu.sv > "$OUT/build_$MODE.log" 2>&1
"$OUT/obj_$MODE/Vtb_gu" +DIR="$OUT" | tee "$OUT/run_$MODE.log" | grep BMUL_GU
grep -q "BMUL_GU PASS" "$OUT/run_$MODE.log"
