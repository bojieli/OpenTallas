#!/bin/bash
set -euo pipefail
out=$(realpath -m "$1");mut=${2:-0};mkdir -p "$out"
root=$(cd "$(dirname "$0")/../../.." && pwd);cd "$root"
cp physical/hbm_generic/argmax18/rtl/ot_hgi_argmax18_m.sv "$out/wrapper.sv"
cp physical/hbm_mtp/rtl/ot_dshbm_argmax_m.sv "$out/native.sv"
case "$mut" in
 0) ;;
 1) sed -i 's/IW=GENERIC18 ? 18 : 17/IW=GENERIC18 ? 17 : 17/' "$out/wrapper.sv";;
 2) sed -i 's/e_key\[k\] > bk\[k\]/e_key[k] >= bk[k]/' "$out/native.sv";;
 3) sed -i "s/{18'b0,cfg_rank} \* {7'b0,cfg_imm_a}/{18'b0,cfg_rank} + {7'b0,cfg_imm_a}/" "$out/wrapper.sv";;
 *) exit 2;;
esac
iverilog -g2012 -s tb_hgi_argmax18 -o "$out/bench.vvp" rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/gpu/ot_gpu_fadd.sv "$out/native.sv" "$out/wrapper.sv" physical/hbm_generic/argmax18/bench/tb_hgi_argmax18.sv > "$out/build.log" 2>&1
vvp -n "$out/bench.vvp" > "$out/sim.log" 2>&1
cat "$out/sim.log"
