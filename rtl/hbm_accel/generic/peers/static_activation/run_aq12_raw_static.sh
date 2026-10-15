#!/usr/bin/env bash
set -euo pipefail
out="${1:?output directory}";inputs="${2:-.}"
mkdir -p "$out"
sources=(ot_hbm_sm_aq_static.sv ot_hdc_fastfp_lat_f12.sv ot_hdc_fp32_f12.sv ot_hdc_fastfp.sv ot_hdc_prefix.sv ot_hdc_sfu.sv ot_hdc_delay.sv tb_aq12_raw_static.sv)
args=();for source in "${sources[@]}";do args+=("$inputs/$source");done
for mut in 0 1 2 3;do
 /usr/bin/time -v -o "$out/compile-$mut.time" iverilog -g2012 -s tb_aq12_raw_static -Ptb_aq12_raw_static.MUT="$mut" -o "$out/gate-$mut.vvp" "${args[@]}" > "$out/compile-$mut.log" 2>&1
 set +e
 /usr/bin/time -v -o "$out/sim-$mut.time" vvp "$out/gate-$mut.vvp" > "$out/sim-$mut.log" 2>&1
 rc=$?
 set -e
 cat "$out/sim-$mut.log"
 if [[ $mut == 0 ]];then [[ $rc == 0 ]];grep -q 'AQ12_RAW_STATIC PASS' "$out/sim-$mut.log"
 else
  [[ $rc != 0 ]];case $mut in 1)needle='AQ12 raw code mismatch';;2)needle='AQ12 exponent mismatch';;3)needle='AQ12 nonfinite fault mismatch';;esac
  grep -q "$needle" "$out/sim-$mut.log"
 fi
done
printf 'PASS actual three-root AQ12 raw SeedX1280 blocks +finite/nonfinite cases; rawcode/exponent/fault mutants killed\n'
