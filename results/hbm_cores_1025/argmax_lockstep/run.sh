#!/bin/bash
cd $(dirname $0)
C="ot_gpu_fadd.sv ot_hdc_fastfp.sv ot_hdc_fp32_add_lat.sv ot_hdc_prefix.sv ot_hdc_fp32_mul_lat.sv ref_r.sv"
for f in 0 1; do for v in new mut1 mut2; do
  ( iverilog -g2012 -o sim_${v}_$f -P tb.FAST=$f tb.sv $v.sv $C >/dev/null 2>&1; echo "== $v FAST=$f: $(timeout 600 vvp -n sim_${v}_$f | grep -E 'LOCKSTEP' | tail -1)" > res_${v}_$f.txt ) &
done; done; wait; cat res_*.txt
