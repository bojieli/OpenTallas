#!/bin/bash
set -euo pipefail
out=$1
mkdir -p "$out"
hdc=(rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_fpu.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv rtl/hdc/ot_hdc_sfu.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fastfp_lat_f12.sv rtl/hdc/ot_hdc_fp32_f12.sv rtl/hdc/ot_hdc_prefix.sv)
common=("${hdc[@]}" physical/hbm_accel_die_views/common/ot_hfd_oreg1.sv rtl/hbm_accel/generic/ot_hgi_fp4qdq.sv rtl/hbm_accel/generic/ot_hgi_quant_decode.sv rtl/test/hbm_accel/generic/tb_hgi_quant_vectors.sv)
core=physical/hbm_accel_die_views/quant/rtl/ot_hfd_actquant_m.sv
verilator --binary --timing -j 8 -Wno-fatal -Wno-lint -Wno-style --top-module tb_hgi_quant_vectors -Mdir "$out/positive.obj" -o sim "${common[@]}" "$core" > "$out/positive.build" 2>&1
"$out/positive.obj/sim" > "$out/positive.log" 2>&1
sed "s/- 10'sd127 + {9'd0,/- 10'sd126 + {9'd0,/" "$core" > "$out/scale_mutant.sv"
verilator --binary --timing -j 8 -Wno-fatal -Wno-lint -Wno-style --top-module tb_hgi_quant_vectors -Mdir "$out/mutant.obj" -o sim "${common[@]}" "$out/scale_mutant.sv" > "$out/mutant.build" 2>&1
set +e
"$out/mutant.obj/sim" > "$out/mutant.log" 2>&1
rc=$?
set -e
printf '%s\n' "$rc" > "$out/mutant.rc"
[[ $rc -ne 0 ]] && grep -q 'CF-QDQ golden mismatch' "$out/mutant.log"
