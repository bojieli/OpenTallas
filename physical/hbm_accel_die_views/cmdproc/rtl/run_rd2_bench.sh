#!/bin/bash
# run_rd2_bench.sh <out dir> (views agent): ot_hfd_cmdproc20_m RDREG 2 (macro-pin capture cmd_r + S_RD2, +1 cycle per
# command) vs the unchanged ot_ds_hbm_cmdproc20, transaction-level (tb_cmdproc_rd_equiv.sv: launch / completion hashes),
# 3 seeds x 300 tokens; negative: a mutant copy whose S_RD2 loads cmd_q from cmd_m (stale-by-design read port word
# replaced) -- must DIFF.  Prints CMDPROC_RD2 PASS / CMDPROC_RD2 FAIL.
O=${1:?}; mkdir -p $O; D=physical/hbm_accel_die_views/cmdproc/rtl
SR=physical/asap7_memory_macros_v2/ot_sram_2rw_512x64_m4_r2c2/ot_sram_2rw_512x64_m4_r2c2.v
sed 's/cmd_q <= cmd_r;   \/\/ cmd_r/cmd_q <= ~cmd_r;  \/\/ MUTANT cmd_r/' $D/ot_hfd_cmdproc20_m.sv | sed 's/module ot_hfd_cmdproc20_m/module ot_hfd_cmdproc20_m_mut/' > $O/mut.sv
grep -q 'MUTANT' $O/mut.sv || { echo "CMDPROC_RD2 FAIL mutant not applied"; exit 1; }
ok=1
for s in 1 2 3; do
  iverilog -g2012 -o $O/pos$s -DSEED=$s -DNTOK=300 -DDUT_B=ot_hfd_cmdproc20_m -DRDREG_B=2 rtl/gpu_sys/ds_hbm_full20/ot_ds_hbm_cmdproc20.sv $D/ot_hfd_cmdproc20_m.sv $SR $D/tb_cmdproc_rd_equiv.sv > $O/c$s.log 2>&1 && vvp -n $O/pos$s > $O/pos$s.log 2>&1
  grep CPR_EQUIV $O/pos$s.log; grep -q 'launch_hash=MATCH cpl_hash=MATCH' $O/pos$s.log && ! grep -q FAIL $O/pos$s.log || ok=0
done
iverilog -g2012 -o $O/neg -DSEED=1 -DNTOK=300 -DDUT_B=ot_hfd_cmdproc20_m_mut -DRDREG_B=2 rtl/gpu_sys/ds_hbm_full20/ot_ds_hbm_cmdproc20.sv $O/mut.sv $SR $D/tb_cmdproc_rd_equiv.sv > $O/cn.log 2>&1 && vvp -n $O/neg > $O/neg.log 2>&1
grep CPR_EQUIV $O/neg.log; grep -q 'DIFF' $O/neg.log && echo CMDPROC_RD2_NEG_DETECTED || { ok=0; echo "neg not detected"; }
[ $ok = 1 ] && echo "CMDPROC_RD2 PASS" || echo "CMDPROC_RD2 FAIL"
