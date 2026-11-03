#!/bin/bash
# DIE-HBM-61/MEM lockstep: r2c2 build vs right-width build (OT_HBM_RW_MACROS) of ot_hep_rx_store; mutants must differ.
set -u
R=$(cd "$(dirname "$0")/../../../../.." && pwd); E=$R/physical/die_plan/hbm/mem_reform_1103/eq; O=${OUT:-/tmp/hbm61mem_eq_hep}; mkdir -p $O
SRC=$R/rtl/hbm_accel/tu/ep_static_20261015/ot_hep_rx_store.sv
OLDM=$R/physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v
NEWM=$R/physical/asap7_memory_macros_v2/ot_sram_1r1w_64x306_m1_r0c0_g306/ot_sram_1r1w_64x306_m1_r0c0_g306.v
sed 's/\.r_addr_in(ra), \.rd_out(mr_w)/.r_addr_in({ra[5:1], ~ra[0]}), .rd_out(mr_w)/' $SRC > $O/mut_addr.sv
sed 's/\.wd_in(dq), \.w_mask_in(1.b1)/.wd_in({dq[305:1], 1'"'"'b0}), .w_mask_in(1'"'"'b1)/' $SRC > $O/mut_data.sv
grep -q "~ra\[0\]" $O/mut_addr.sv && grep -q "dq\[305:1\]" $O/mut_data.sv || { echo "MUTANT SED FAILED"; exit 2; }
one() {  # one seed: lockstep + mutants; prints PASS/FAIL lines
  seed=$1
  b() { iverilog -g2012 -DOT_MEM_NO_INIT=1 -DTB_SEED=$seed -DTB_CYC=${CYC:-6000} -DTB_MUT=$3 $2 -o $O/$1_$seed.vvp $E/tb_hep.sv $4 $OLDM $NEWM && vvp -n $O/$1_$seed.vvp > $O/$1_$seed.log; }
  b ref "" 0 $SRC; b rw "-DOT_HBM_RW_MACROS" 0 $SRC
  b m_addr "-DOT_HBM_RW_MACROS" 0 $O/mut_addr.sv; b m_data "-DOT_HBM_RW_MACROS" 0 $O/mut_data.sv; b m_mut "-DOT_HBM_RW_MACROS" 1 $SRC
  echo "seed $seed $(grep COVER $O/rw_$seed.log)"
  if [ -s $O/ref_$seed.log ] && cmp -s $O/ref_$seed.log $O/rw_$seed.log; then echo "seed $seed LOCKSTEP EQUAL ($(wc -l < $O/ref_$seed.log) lines)"; else echo "seed $seed LOCKSTEP DIFF FAIL"; fi
  for m in m_addr m_data m_mut; do cmp -s $O/ref_$seed.log $O/${m}_$seed.log && echo "seed $seed $m SURVIVED FAIL" || echo "seed $seed $m killed"; done
}
for seed in 1 7 1103; do one $seed > $O/seed_$seed.txt 2>&1 & done; wait
cat $O/seed_*.txt; ! grep -q FAIL $O/seed_*.txt
