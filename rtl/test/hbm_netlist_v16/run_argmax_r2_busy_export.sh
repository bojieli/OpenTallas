#!/usr/bin/env bash
# Lockstep busy-export bench (HBM-NATIVE 10-17): r2 (busy export flop) vs the closed e4dc0b651 r2 RTL, every output, every
# edge. Usage: run_argmax_r2_busy_export.sh OUT [mut] [seed]; mut=1 builds the OT_ARGMAX_BUSY_EXPORT_MUT mutant.
# Exit 0 iff the run prints ARGMAX_R2_BUSY_EXPORT PASS.
set -u
out=${1:-$(mktemp -d)}; mut=${2:-0}; seed=${3:-1}; mkdir -p "$out"
D=(); [ "$mut" = 1 ] && D=(-DOT_ARGMAX_BUSY_EXPORT_MUT)
A=(rtl/test/hbm_netlist_v16/tb_argmax_r2_busy_export.sv rtl/hbm_accel/generic/ot_hbm_argmax_static_sw_vm_r2.sv
   rtl/test/hbm_netlist_v16/ref_argmax_static_sw_vm_r2_e4dc.sv rtl/lib/ot_rst_relay.sv
   physical/hbm_generic/argmax18/rtl/ot_hgi_argmax18_m.sv physical/hbm_generic/argmax18/rtl/ot_hgi_argmax18_value_m.sv
   rtl/gpu/ot_gpu_fadd.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv)
iverilog -g2012 -DSEED=$seed "${D[@]}" -o "$out/be$mut" "${A[@]}" > "$out/build$mut.log" 2>&1 || { echo "BUILD FAIL"; cat "$out/build$mut.log"; exit 2; }
r=$(vvp -n "$out/be$mut" 2>&1 | grep -Ev '\$finish|^VCD' | tail -8); echo "MUT=$mut $r"
case "$r" in *"ARGMAX_R2_BUSY_EXPORT PASS"*) exit 0;; *) exit 1;; esac
