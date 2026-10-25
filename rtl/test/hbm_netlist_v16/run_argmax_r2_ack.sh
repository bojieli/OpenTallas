#!/usr/bin/env bash
# HBM-BIND B2 (2026-10-24): ot_hbm_argmax_static_sw_vm_r2 CNTW / large-ACK bench (tb_argmax_r2_ack.sv).
#   PASS legs: XA 0 (both engines ACK 13), XA 49 (ACK 62, last 6-bit value), XA 98 (ACK 111 = B2m hub echo, CNTW 8).
#   FAIL leg (mutant): XA 98 CMUT 1 (engine 1 forced to the as-built 6-bit counter).
# usage: run_argmax_r2_ack.sh OUT   (run from the repo root)
set -uo pipefail
out=${1:?out}; mkdir -p "$out"; fail=0
F=(rtl/test/hbm_netlist_v16/tb_argmax_r2_ack.sv rtl/hbm_accel/generic/ot_hbm_argmax_static_sw_vm_r2.sv
   rtl/hbm_accel/index/ot_hbm_idx_vm_share_static.sv rtl/hbm_accel/index/ot_hbm_idx_vm_share_static_am.sv rtl/lib/ot_rst_relay.sv
   physical/hbm_generic/argmax18/rtl/ot_hgi_argmax18_m.sv physical/hbm_generic/argmax18/rtl/ot_hgi_argmax18_value_m.sv
   physical/hbm_mtp/rtl/ot_dshbm_argmax_m.sv rtl/gpu/ot_gpu_fadd.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fp32_add_lat.sv
   rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv)
L=("0 0 pass" "49 0 pass" "98 0 pass" "98 1 fail")
for l in "${L[@]}"; do set -- $l; t="x$1_c$2"
  ( iverilog -g2012 -DXA=$1 -DCMUT=$2 -DNREC=${NREC:-150} -o "$out/$t" "${F[@]}" > "$out/$t.build.log" 2>&1 && vvp -n "$out/$t" > "$out/$t.log" 2>&1 ) &
done; wait
for l in "${L[@]}"; do set -- $l; t="x$1_c$2"
  r=$(grep -E 'ARGMAX_R2_ACK (PASS|FAIL)' "$out/$t.log" 2>/dev/null | tail -1); s=$(grep '^requests' "$out/$t.log" 2>/dev/null | tail -1)
  echo "$t expect=$3 :: ${r:-NO RESULT} :: $s"
  if [ "$3" = pass ]; then echo "$r" | grep -q 'ARGMAX_R2_ACK PASS' || fail=1; else echo "$r" | grep -q 'ARGMAX_R2_ACK FAIL' || fail=1; fi
done
[ $fail = 0 ] && echo "ARGMAX_R2_ACK_GATE PASS" || { echo "ARGMAX_R2_ACK_GATE FAIL"; exit 1; }
