#!/bin/bash
# HG-SPLIT 11-03: cosim A/B of the ep EX join fix (EX_ADD / EX_PAD, rtl/test/qwen_kv_die/tb_qkd_astk_strip_exadd.sv).
# usage: astk_exadd_bench.sh OUTDIR [J]   PASS runs: CD 1 / 2 (EXM 2 / 4), CD 2 + PADX 6; must FAIL: FIX 0, KVD_STMUT 6, 7.
set -u
R=$(cd "$(dirname "$0")/../.." && pwd); OUT=${1:-/tmp/astk_exadd}; J=${2:-4}; mkdir -p "$OUT"; rm -f "$OUT"/*.res
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
[ -x "$V" ] || V=$(command -v verilator)
M=$R/physical/qkd_astk_strip/macros
SRC="$R/rtl/test/qwen_kv_die/tb_qkd_astk_strip_exadd.sv $R/rtl/test/qwen_kv_die/qkd_astk_strip_st_exadd.sv
 $R/rtl/qwen_sys/split_20261014/qkd_astk_strip_st.sv $R/rtl/qwen_sys/kv_plan_leaves_1023/qkd_astk_ep_s_e.sv
 $R/rtl/qwen_sys/kv_plan_leaves_1023/qkd_astk_ep_s_head_e.sv
 $R/rtl/qwen_sys/split_20261014/qkd_astk_static_leaves.sv $R/rtl/qwen_sys/kv_die_20261009/qkd_astk_leaves.sv
 $R/rtl/qwen_sys/split_20261014/qkd_astk_phys.sv $R/rtl/hdc/ot_hdc_delay.sv $R/rtl/hdc/ot_hdc_fp32_add_lat.sv $R/rtl/hdc/ot_hdc_fp32_add_lat_nr.sv
 $R/rtl/hdc/nearhbm/ot_qwen_nearhbm_sfu_p.sv $R/rtl/hdc/ot_hdc_sfu.sv $R/rtl/hdc/ot_hdc_prefix.sv $R/rtl/hdc/ot_hdc_fastfp.sv
 $R/rtl/hdc/ot_hdc_fp32_mul_lat.sv $M/ot_sram_1r1w_256x128_m1_r2c2/ot_sram_1r1w_256x128_m1_r2c2.v
 $M/ot_sram_1r1w_64x128_m1_r2c2/ot_sram_1r1w_64x128_m1_r2c2.v"
one() {  # tag expect(PASS|FAIL) mut gparams...
  local tag=$1 exp=$2 mut=$3; shift 3
  "$V" --binary -j 4 --timing -Wno-fatal -Wno-lint -Wno-style --top-module tb_qkd_astk_strip_exadd -DKVD_HEADS=1 -DKVD_STMUT=$mut "$@" \
    -Mdir "$OUT/$tag" -o Vtb $SRC > "$OUT/$tag.build.log" 2>&1 || { echo "BUILD_FAIL $tag" | tee "$OUT/$tag.res"; return; }
  "$OUT/$tag/Vtb" > "$OUT/$tag.log" 2>&1
  local got; got=$(grep -m1 -E '^(PASS|FAIL)' "$OUT/$tag.log" || echo "NORESULT")
  if [ "$exp" = PASS ]; then case "$got" in PASS*) echo "PASS   $tag $got";; *) echo "FAIL   $tag $got";; esac
  else case "$got" in FAIL*) echo "CAUGHT $tag $got";; *) echo "MISSED $tag $got";; esac; fi | tee "$OUT/$tag.res"
  rm -rf "$OUT/$tag"
}
job() { while [ "$(jobs -rp | wc -l)" -ge "$J" ]; do wait -n; done; one "$@" & }
job cd1 PASS 0 -GCD=1
job cd2 PASS 0 -GCD=2
job cd2pad6 PASS 0 -GCD=2 -GPADX=6
job nofix FAIL 0 -GCD=2 -GFIX=0
job mut6 FAIL 6 -GCD=2
job mut7 FAIL 7 -GCD=2
wait
NP=$(cat "$OUT"/*.res | grep -c '^PASS'); NC=$(cat "$OUT"/*.res | grep -c '^CAUGHT'); NF=$(cat "$OUT"/*.res | grep -vc '^PASS\|^CAUGHT')
echo "SUMMARY pass $NP mutants_caught $NC fail $NF"
[ "$NF" = 0 ]
