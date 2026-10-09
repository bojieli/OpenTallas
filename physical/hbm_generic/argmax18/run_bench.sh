#!/bin/bash
set -euo pipefail
out=$(realpath -m "$1");mut=${2:-0};mkdir -p "$out"
root=$(cd "$(dirname "$0")/../../.." && pwd);cd "$root"
cp physical/hbm_generic/argmax18/rtl/ot_hgi_argmax18_m.sv "$out/wrapper.sv"
cp physical/hbm_mtp/rtl/ot_dshbm_argmax_m.sv "$out/native.sv"
cp physical/hbm_generic/argmax18/rtl/ot_hgi_argmax18_value_m.sv "$out/value.sv"
case "$mut" in
 0) ;;
 1) sed -i 's/IW=GENERIC18 ? 18 : 17/IW=GENERIC18 ? 17 : 17/' "$out/wrapper.sv";;
 2) sed -i 's/e_key\[k\] > bk\[k\]/e_key[k] >= bk[k]/' "$out/value.sv";;
 3) sed -i "s/{18'b0,rank_q} \* {7'b0,imm_q}/{18'b0,rank_q} + {7'b0,imm_q}/" "$out/wrapper.sv";;
 4) sed -i "s/out_value <= tbits\[LL\]\[0\]/out_value <= 32'b0/" "$out/value.sv";;
 5) sed -i "s/e_bits\[q\] <= a_val\[32\*q +: 32\]/e_bits[q] <= (a_val[32*q+30 -: 8] == 8'hff \&\& a_val[32*q +: 23] != 0) ? 32'h7fc00000 : a_val[32*q +: 32]/" "$out/value.sv";;
 6) sed -i "s/out_value <= tbits\[LL\]\[0\]/out_value <= (tbits[LL][0] == 32'h80000000) ? 32'h0 : tbits[LL][0]/" "$out/value.sv";;
 *) exit 2;;
esac
iverilog -g2012 -s tb_hgi_argmax18 -o "$out/bench.vvp" rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/gpu/ot_gpu_fadd.sv "$out/native.sv" "$out/value.sv" "$out/wrapper.sv" physical/hbm_generic/argmax18/bench/tb_hgi_argmax18.sv > "$out/build.log" 2>&1
set +e
vvp -n "$out/bench.vvp" > "$out/sim.log" 2>&1
sim_rc=$?
set -e
cat "$out/sim.log"
exit "$sim_rc"
