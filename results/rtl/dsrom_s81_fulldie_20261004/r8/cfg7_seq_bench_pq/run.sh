#!/bin/bash
# s81-die-2 2026-10-08 (TA-10): ot_s81_cfg7_seq exact gate at PQ 0 and PQ 1 (lockstep vs ot_v41_pair_pq_ld_frontend) + mutants.
# PASS: gold PQ0 / PQ1 rc 0; every mutant rc != 0.
cd $(dirname $0); R=../../../../..
F="$R/rtl/v41die/ot_s81_cfg7_seq.sv $R/rtl/v41die/test/tb_ot_s81_cfg7_seq.sv $R/physical/dsrom_qx10_parent_context/parent_loader/ot_v41_pair_pq_ld_frontend.sv $R/physical/asap7_memory_macros/ot_rom_4096x72_m8/ot_rom_4096x72_m8.v"
: > rc.txt
run() { n=$1; pq=$2; d=$3
  iverilog -g2012 -o sim_$n -Ptb_ot_s81_cfg7_seq.PQ=$pq $d -s tb_ot_s81_cfg7_seq $F > build_$n.log 2>&1 && vvp -n sim_$n > run_$n.log 2>&1; echo "$n rc=$?" >> rc.txt; }
run gold_pq0 0 '' & run gold_pq1 1 '' &
run MUT_BANK_pq1 1 -DOT_S81_CFG7_MUT_BANK & run MUT_STRIDE_pq1 1 -DOT_S81_CFG7_MUT_STRIDE &
run MUT_TAG_pq1 1 -DOT_S81_CFG7_MUT_TAG & run MUT_NOFAULT_pq1 1 -DOT_S81_CFG7_MUT_NOFAULT & run MUT_NOHOLD_pq1 1 -DOT_S81_CFG7_MUT_NOHOLD &
wait; rm -f sim_*; sort rc.txt
