#!/bin/bash
# sys-takeover 2026-10-09: committed HC mean-capture gate (tb_hc_mean_capture) on ECC_PIPE=1 MREG=1: full-shape positive,
# the six command/beat negatives, plain VM reader (PROTECT=0), CE / UE injection into the SRAM SECDED; neg = the TREE
# (reduction order) and ALIAS (layer alias) mutants, which must fail.      hc_mean_mreg_bench.sh pos|neg OUT
set -uo pipefail
mode=$1; out=$2; mkdir -p "$out"
S=(rtl/experimental/dsrom_hc_capture_20261009/ot_dsrom_hc_secded_pipe.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fastfp.sv
 rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv rtl/dsrom_sys/s81_ctrl/ot_s81_secded.sv
 physical/asap7_memory_macros_v2/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v
 rtl/experimental/dsrom_hc_capture_20261009/ot_dsrom_hc_mean_capture.sv rtl/experimental/dsrom_hc_capture_20261009/ot_dsrom_hc_input_reader.sv
 rtl/test/dsrom_hc_capture_20261009/tb_hc_mean_capture.sv)
D=(-DHC_ECC_PIPE -DHC_MREG)
python3 tools/dsrom_hc_mean_capture_vectors.py --out "$out/synthetic" >"$out/vectors.log" 2>&1 || { echo HCM_BENCH_ERROR; exit 2; }
run() { local tag=$1; shift; iverilog -g2012 "${D[@]}" "$@" -s tb_hc_mean_capture -o "$out/$tag.vvp" "${S[@]}" >"$out/$tag.build.log" 2>&1 || { echo "HCM_BENCH_ERROR build $tag"; exit 2; }; }
if [[ $mode == pos ]]; then
  ok=1
  run base; vvp "$out/base.vvp" +vectors="$out/synthetic" >"$out/positive.log" 2>&1 && grep -q '^PASS full shape' "$out/positive.log" || ok=0
  for bad in 1 2 3 4 5 10; do vvp "$out/base.vvp" +vectors="$out/synthetic" +bad=$bad >"$out/negative_$bad.log" 2>&1 && grep -q '^PASS negative' "$out/negative_$bad.log" || ok=0; done
  run reader -DHC_VM_READER -DHC_READER_PLAIN; vvp "$out/reader.vvp" +vectors="$out/synthetic" >"$out/reader.log" 2>&1 && grep -q '^PASS full shape' "$out/reader.log" || ok=0
  run ce -DHC_INJECT_CE; vvp "$out/ce.vvp" +vectors="$out/synthetic" >"$out/ce.log" 2>&1 && grep -q '^PASS full shape.*CE=120' "$out/ce.log" || ok=0
  run ue -DHC_INJECT_UE; vvp "$out/ue.vvp" +vectors="$out/synthetic" >"$out/ue.log" 2>&1; grep -qi 'PASS' "$out/ue.log" || ok=0
  tail -1 "$out/positive.log"; tail -1 "$out/ce.log"; tail -1 "$out/ue.log"
  [[ $ok == 1 ]] && { echo HC_MEAN_MREG_PASS; exit 0; }; echo HC_MEAN_MREG_FAIL; exit 1
fi
n=0
for m in TREE ALIAS; do run $m -DHC_MUT_$m; vvp "$out/$m.vvp" +vectors="$out/synthetic" >"$out/$m.log" 2>&1 && continue; grep -q 'mean/identity/order mismatch' "$out/$m.log" && n=$((n+1)); done
[[ $n == 2 ]] && { echo "HC_MEAN_MREG_NEG_DETECTED 2/2"; exit 1; }; echo "HC_MEAN_MREG_NEG_MISSED $n/2"; exit 0
