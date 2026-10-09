#!/bin/bash
# sys-takeover 2026-10-09: committed HC reader gate (tb_hc_mean_capture HC_VM_READER + HC_DISTRIBUTED, synthetic
# full-shape vectors and the four bad-native-read negatives) on the PROTECT=0 plain reader.
#   hc_reader_plain_bench.sh pos|neg OUT
set -uo pipefail
mode=$1; out=$2; mkdir -p "$out"
src=(rtl/experimental/dsrom_hc_capture_20261009/ot_dsrom_hc_secded_pipe.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fastfp.sv
 rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv rtl/dsrom_sys/s81_ctrl/ot_s81_secded.sv
 physical/asap7_memory_macros_v2/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v
 rtl/experimental/dsrom_hc_capture_20261009/ot_dsrom_hc_mean_capture.sv rtl/experimental/dsrom_hc_capture_20261009/ot_dsrom_hc_input_reader.sv
 rtl/experimental/dsrom_hc_capture_20261009/ot_dsrom_hc_seed_join.sv rtl/test/dsrom_hc_capture_20261009/tb_hc_mean_capture.sv)
iverilog -g2012 -DHC_READER_PLAIN -s tb_hc_mean_capture -DHC_VM_READER -DHC_DISTRIBUTED -o "$out/reader.vvp" "${src[@]}" >"$out/elaborate.log" 2>&1 || { cat "$out/elaborate.log"; echo HCRP_BENCH_ERROR; exit 2; }
python3 tools/dsrom_hc_mean_capture_vectors.py --out "$out/synthetic" >"$out/vectors.log" 2>&1 || { echo HCRP_BENCH_ERROR vectors; exit 2; }
if [[ $mode == pos ]]; then
  vvp "$out/reader.vvp" +vectors="$out/synthetic" >"$out/reader.log" 2>&1; rc=$?; tail -3 "$out/reader.log"
  if [[ $rc == 0 ]] && ! grep -qi fatal "$out/reader.log"; then echo HC_READER_PLAIN_PASS; exit 0; fi
  echo HC_READER_PLAIN_FAIL; exit 1
fi
n=0
for bad in 6 7 8 10; do
  vvp "$out/reader.vvp" +vectors="$out/synthetic" +bad="$bad" >"$out/negative_$bad.log" 2>&1 && { echo "bad $bad ESCAPED"; exit 0; }
  grep -q 'native H reader fault' "$out/negative_$bad.log" && n=$((n+1))
done
[[ $n == 4 ]] && { echo "HC_READER_PLAIN_NEG_DETECTED 4/4"; exit 1; }
echo "HC_READER_PLAIN_NEG_UNCLEAR $n/4"; exit 0
