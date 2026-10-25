#!/usr/bin/env bash
# HBM-BIND B2 (lane hbm-bind-idx 2026-10-24): ot_hbm_argmax_static_sw_vm_r2 SID strap bench (tb_argmax_r2_sid.sv).
#   PASS legs: S 0 (default vs the unchanged as-built master) at DIE 0 / DIE 1; S 3 (vs the as-built text with strap 3)
#              at DIE 0 / DIE 1.   FAIL leg (mutant): S 3 SIDMUT (DUT left at the as-built SW strap 0).
# usage: run_argmax_r2_sid.sh OUT REFDIR   (REFDIR from rtl/test/hbm_idx_static/mk_idx_b2_refs.sh); run from the repo root.
set -uo pipefail
out=${1:?out}; refs=${2:?refdir}; mkdir -p "$out"; fail=0
F=(rtl/test/hbm_netlist_v16/tb_argmax_r2_sid.sv rtl/hbm_accel/generic/ot_hbm_argmax_static_sw_vm_r2.sv "$refs/argmax_ref.sv" "$refs/argmax_ref3.sv"
   rtl/lib/ot_rst_relay.sv physical/hbm_generic/argmax18/rtl/ot_hgi_argmax18_m.sv physical/hbm_generic/argmax18/rtl/ot_hgi_argmax18_value_m.sv
   physical/hbm_mtp/rtl/ot_dshbm_argmax_m.sv rtl/gpu/ot_gpu_fadd.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fp32_add_lat.sv
   rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv)
one() {  # S DIE MUT(0/1) expect
  t="s$1_d$2_m$3"; def=(); [ "$3" = 1 ] && def=(-DSIDMUT)
  iverilog -g2012 -DS=$1 -DDIE=$2 "${def[@]}" -o "$out/$t" "${F[@]}" > "$out/$t.build.log" 2>&1 || { echo "BUILD_FAIL $t"; tail -5 "$out/$t.build.log"; fail=1; return; }
  vvp -n "$out/$t" > "$out/$t.log" 2>&1
  r=$(grep -o 'ARGMAX_R2_SID [A-Z]* checks=[0-9]* errors=[0-9]*' "$out/$t.log" | tail -1); s=$(grep 'ARGMAX_R2_SID S=' "$out/$t.log" | tail -1)
  echo "$t expect=$4 :: $r :: $s"
  if [ "$4" = pass ]; then echo "$r" | grep -q ' PASS ' || fail=1; else echo "$r" | grep -Eq ' FAIL checks=[0-9]+ errors=[1-9]' || fail=1; fi
}
one 0 0 0 pass; one 0 1 0 pass; one 3 0 0 pass; one 3 1 0 pass; one 3 0 1 fail
[ $fail = 0 ] && echo "ARGMAX_R2_SID_GATE PASS" || { echo "ARGMAX_R2_SID_GATE FAIL"; exit 1; }
