#!/bin/bash
# QC-PLAN-F4A narrowed-swap lockstep: 3 seeds x 20000 cycles new vs old, + vmr and rp1 address mutants (must mismatch)
W=$(cd $(dirname $0)/../../.. && pwd); cd $W; S=results/qc_plan_f4a/swap; D=$S/lockstep
M1=physical/asap7_memory_macros_v2/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v
M2=physical/asap7_memory_macros_v2_col/ot_sram_1r1w_1024x256_m1b2_r2c2_ns/ot_sram_1r1w_1024x256_m1b2_r2c2_ns.v
M3=physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v
M4=physical/asap7_memory_macros_v2/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v
for v in new mut_vmr mut_rp1; do iverilog -g2012 -s tb -o $D/$v.vvp $S/tb_swap2.v $S/$v.sv $S/old_suffixed.sv $M1 $M2 $M3 $M4 > $D/${v}_compile.log 2>&1 || echo COMPILE_FAIL $v; done
cd $D; rm -f *_seed*.log
for s in 1 2 3; do prlimit --as=4000000000 timeout 5400 vvp -n new.vvp +seed=$s +n=20000 > new_seed$s.log 2>&1 & done
for v in mut_vmr mut_rp1; do prlimit --as=4000000000 timeout 5400 vvp -n $v.vvp +seed=1 +n=2000 > ${v}_seed1.log 2>&1 & done
wait
grep -H RESULT *_seed*.log
