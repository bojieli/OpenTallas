#!/bin/bash
# KV-DCAL2 10-19: ot_qkh_ktree_lk (per-lane KPV lockstep check) bench.  usage: ktree_lk_bench.sh OUTDIR [MUT]
#   MUT 0: PASS (miter == ot_qkh_ktree in lockstep, 32/32 lane skew/drop/duplicate injections detected)
#   MUT 1: lanes ignored (old kpv_in[0]-only wiring) -> FAIL (detected < 32)
set -e
R=$(cd "$(dirname "$0")/../.." && pwd); OUT=$1; MUT=${2:-0}
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
[ -x "$V" ] || V=$(command -v verilator)
mkdir -p "$OUT"
H=$R/rtl/hdc
SRC="$R/rtl/test/qwen_kv_die/tb_qkh_ktree_lk.sv $H/nearhbm/ot_qkh_ktree_lk.sv $H/nearhbm/ot_qkh_subtiles.sv
 $H/nearhbm/ot_qwen_nearhbm_prod.sv $R/rtl/lib/ot_rst_relay.sv $H/ot_hdc_delay.sv $H/ot_hdc_fp32_add_lat_nr.sv
 $H/ot_hdc_fp32_add_lat.sv $H/ot_hdc_fp32_mul_lat.sv $H/ot_hdc_prefix.sv $H/ot_hdc_fastfp.sv"
"$V" --version | tee "$OUT/verilator.version"
"$V" --binary -j 8 --timing -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD --top-module tb_qkh_ktree_lk -DKLK_MUT=$MUT \
  -Mdir "$OUT/obj" -o Vtb $SRC > "$OUT/build.log" 2>&1 || { tail -30 "$OUT/build.log"; echo "FAIL ktree_lk build"; exit 1; }
"$OUT/obj/Vtb" > "$OUT/run.log" 2>&1 || true
grep -E '^(PASS|FAIL|MISMATCH)' "$OUT/run.log" | head -12
grep -q '^PASS ktree_lk' "$OUT/run.log"
