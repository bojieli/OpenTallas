#!/usr/bin/env bash
# ot_hbm_argmax_static_sw_vm_r2 vs ot_hbm_argmax_static_sw_vm (HBM-TILES-B 10-17). PASS = MUT0 PASS, MUT1..3 FAIL.
# Usage: run_argmax_r2.sh OUT            -> full bench (ARGMAX_R2_BENCH PASS|FAIL)
#        run_argmax_r2.sh OUT <m>        -> one run, MUT=<m> only; exit 0 iff it prints ARGMAX_R2 PASS (mutant job benches, expect=fail)
set -u
out=${1:-$(mktemp -d)}; one=${2:-}; mkdir -p "$out"; rc=0
A=(rtl/test/hbm_netlist_v16/tb_argmax_sw_vm_r2.sv rtl/hbm_accel/generic/ot_hbm_argmax_static_sw_vm_r2.sv
   rtl/hbm_accel/generic/ot_hbm_argmax_static_sw_vm.sv rtl/hbm_accel/generic/ot_hbm_argmax_static.sv rtl/lib/ot_rst_relay.sv
   rtl/hbm_accel/index/ot_hbm_idx_vm_share_static.sv rtl/hbm_accel/index/ot_hbm_idx_vm_share_static_am.sv
   physical/hbm_generic/argmax18/rtl/ot_hgi_argmax18_m.sv physical/hbm_generic/argmax18/rtl/ot_hgi_argmax18_value_m.sv
   physical/hbm_mtp/rtl/ot_dshbm_argmax_m.sv rtl/gpu/ot_gpu_fadd.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv)
if [ -n "$one" ]; then
  iverilog -g2012 -DMUT=$one -o "$out/r$one" "${A[@]}" > "$out/build$one.log" 2>&1 || { echo "BUILD FAIL $one"; exit 2; }
  r=$(vvp -n "$out/r$one" 2>&1 | grep -Ev '\$finish|^VCD' | tail -2 | tr '\n' ' '); echo "MUT=$one $r"
  case "$r" in *"ARGMAX_R2 PASS"*) exit 0;; *) exit 1;; esac
fi
for m in 0 1 2 3; do
  iverilog -g2012 -DMUT=$m -o "$out/r$m" "${A[@]}" > "$out/build$m.log" 2>&1 || { echo "BUILD FAIL $m"; rc=1; continue; }
  r=$(vvp -n "$out/r$m" 2>&1 | grep -Ev '\$finish|^VCD' | tail -2 | tr '\n' ' '); echo "MUT=$m $r"
  if [ $m -eq 0 ]; then case "$r" in *"ARGMAX_R2 PASS"*) ;; *) rc=1;; esac; else case "$r" in *"ARGMAX_R2 FAIL"*) ;; *) rc=1;; esac; fi
done
[ $rc -eq 0 ] && echo "ARGMAX_R2_BENCH PASS" || echo "ARGMAX_R2_BENCH FAIL"; exit $rc
