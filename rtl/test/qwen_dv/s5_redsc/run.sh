#!/usr/bin/env bash
set -euo pipefail
work=$1
leaf=${2:-rtl/qwen_dv/s5/qfd_dv_s5_leaves.sv}
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
verilator --version | grep '5.050'
python3 rtl/test/qwen_dv/s5_redsc/generate.py "$leaf" "$work/generated"
for kind in red sc; do
 for mut in 0 1; do
  dir="$work/${kind}_m${mut}"
  mkdir -p "$dir"
  verilator --binary --timing -j 4 -Wno-fatal +define+MUT=$mut --top-module "tb_$kind" --Mdir "$dir/obj" "$leaf" "$work/generated/references.sv" "$work/generated/tb_$kind.sv" rtl/qwen_dv/qfd_dv_scalar2.sv rtl/hdc/{ot_hdc_vreduce,ot_hdc_fastfp,ot_hdc_fp32_add_lat,ot_hdc_fp32_mul_lat,ot_hdc_prefix,ot_hdc_delay,ot_hdc_sfu,ot_hdc_sfu_q}.sv > "$dir/build.log" 2>&1
  set +e
  "$dir/obj/Vtb_$kind" > "$dir/run.log" 2>&1
  rc=$?
  set -e
  if [[ $mut == 0 ]]; then [[ $rc == 0 ]]; grep 'PASS' "$dir/run.log"; else [[ $rc != 0 ]]; grep 'MISMATCH' "$dir/run.log"; fi
 done
done
