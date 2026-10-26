#!/bin/bash
# QC-SU-F4-2 lockstep: 3 seeds x 20000 cycles + compile
cd /srv/opentallas-scratch2/claude/wt/qc-su-f4-2-1026
D=results/qc_su_f4/r2/lockstep
M1=physical/asap7_memory_macros_v2/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v
M2=physical/asap7_memory_macros_v2_col/ot_sram_1r1w_1024x256_m1b2_r2c2_ns/ot_sram_1r1w_1024x256_m1b2_r2c2_ns.v
M3=physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v
M4=physical/asap7_memory_macros_v2/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v
iverilog -g2012 -s tb -o $D/ls.vvp results/qc_su_f4/r2/tb_swap.v rtl/qwen_dv/s5/qfd_dv_s5_vm8x.sv $D/vm8x_old_suffixed.sv $M1 $M2 $M3 $M4 > $D/ls_compile.log 2>&1
cd $D; rm -f ls_seed*.log
for s in 1 2 3; do prlimit --as=4000000000 timeout 5400 vvp -n ls.vvp +seed=$s +n=20000 > ls_seed$s.log 2>&1 & done
wait
grep -H "RESULT\|MISMATCH\|rror" ls_seed*.log
