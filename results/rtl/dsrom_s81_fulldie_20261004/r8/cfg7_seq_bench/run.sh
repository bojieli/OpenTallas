#!/bin/bash
cd $(dirname $0)
F='ot_s81_cfg7_seq.sv tb_ot_s81_cfg7_seq.sv ot_v41_pair_pq_ld_frontend.sv ot_rom_4096x72_m8.v'
for v in gold MUT_BANK MUT_STRIDE; do
  d=''; [ $v != gold ] && d=-DOT_S81_CFG7_$v
  iverilog -g2012 -o sim_$v $d -s tb_ot_s81_cfg7_seq $F > build_$v.log 2>&1 && vvp -n sim_$v > run_$v.log 2>&1; echo "$v rc=$?" >> rc.txt
done
