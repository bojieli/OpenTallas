#!/bin/bash
# DIE-HBM-61/MEM lockstep: keybuf_slice r2c2 vs OT_HBM_RW_MACROS build; address/data mutants of the new path must differ.
set -u
R=$(cd "$(dirname "$0")/../../../../.." && pwd); E=$R/physical/die_plan/hbm/mem_reform_1103/eq; O=${OUT:-/tmp/hbm61mem_eq_kb}; mkdir -p $O
SRC=$R/rtl/hbm_next/idxn/ot_hnx_idxn_keybuf_slice.sv
M="$R/physical/asap7_memory_macros/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v $R/physical/asap7_memory_macros_v2/ot_sram_1r1w_256x256_m2_r0c0_g256/ot_sram_1r1w_256x256_m2_r0c0_g256.v $R/physical/asap7_memory_macros_v2/ot_sram_1r1w_256x64_m2_r0c0_g64/ot_sram_1r1w_256x64_m2_r0c0_g64.v"
sed 's/ot_sram_1r1w_256x64_m2_r0c0_g64 mem(.clk(clk),.r_ce_in(pre_v),.r_addr_in(pre_index)/ot_sram_1r1w_256x64_m2_r0c0_g64 mem(.clk(clk),.r_ce_in(pre_v),.r_addr_in(pre_index^8'"'"'d1)/' $SRC > $O/mut_addr.sv
sed 's/.wd_in(wd\[m\*256+:256\]),.w_mask_in(1.b1)/.wd_in(wd[m*256+:256]^256'"'"'d1),.w_mask_in(1'"'"'b1)/' $SRC > $O/mut_data.sv
grep -q "pre_index^8'd1" $O/mut_addr.sv && grep -q "256'd1)" $O/mut_data.sv || { echo "MUTANT SED FAILED"; exit 2; }
one() { seed=$1
  b() { iverilog -g2012 -DTB_SEED=$seed -DTB_CYC=${CYC:-3000} $2 -o $O/$1_$seed.vvp $E/tb_kb.sv $3 $M && vvp -n $O/$1_$seed.vvp > $O/$1_$seed.log; }
  b ref "" $SRC; b rw -DOT_HBM_RW_MACROS $SRC; b m_addr -DOT_HBM_RW_MACROS $O/mut_addr.sv; b m_data -DOT_HBM_RW_MACROS $O/mut_data.sv
  echo "seed $seed replay-cycles-with-key=$(awk '$2==0' $O/rw_$seed.log | wc -l) fault_end=$(tail -2 $O/rw_$seed.log | head -1 | cut -d' ' -f2)"
  if [ -s $O/ref_$seed.log ] && cmp -s $O/ref_$seed.log $O/rw_$seed.log; then echo "seed $seed LOCKSTEP EQUAL ($(wc -l < $O/ref_$seed.log) lines)"; else echo "seed $seed LOCKSTEP DIFF FAIL"; fi
  for m in m_addr m_data; do cmp -s $O/ref_$seed.log $O/${m}_$seed.log && echo "seed $seed $m SURVIVED FAIL" || echo "seed $seed $m killed"; done
}
for seed in 1 7 1103; do one $seed > $O/seed_$seed.txt 2>&1 & done; wait
cat $O/seed_*.txt; ! grep -q FAIL $O/seed_*.txt
