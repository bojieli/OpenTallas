#!/bin/bash
# DIE-HBM-61/MEM lockstep: cp_rxs memory leaves (landing256 + llr replay leaf) r2c2 vs OT_HBM_RW_MACROS; mutants must differ.
set -u
R=$(cd "$(dirname "$0")/../../../../.." && pwd); E=$R/physical/die_plan/hbm/mem_reform_1103/eq; O=${OUT:-/tmp/hbm61mem_eq_cp}; mkdir -p $O
LAND=$R/rtl/hbm_accel/io_native_20261014/ot_hbm_host_landing256.sv; LLR=$R/rtl/qwen_sys/split_20261014/ot_qkvd_d2d_llr.sv
V1=$R/physical/asap7_memory_macros; V2=$R/physical/asap7_memory_macros_v2
M="$V1/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v $V1/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v"
for n in ot_sram_1r1w_64x306_m1_r0c0_g306 ot_sram_1r1w_64x141_m1_r0c0_g141 ot_sram_1r1w_64x32_m1_r0c0_g32 ot_sram_1r1w_256x256_m2_r0c0_g256; do M="$M $V2/$n/$n.v"; done
python3 - $LLR $O/mut_llr_addr.sv $LAND $O/mut_land_data.sv <<'PY'
import sys
s=open(sys.argv[1]).read(); a=s.index("ot_sram_1r1w_64x141_m1_r0c0_g141 u_sram ("); b=s.index(".r_addr_in(ra)", a)
open(sys.argv[2],"w").write(s[:b]+".r_addr_in({ra[5:1],~ra[0]})"+s[b+len(".r_addr_in(ra)"):])
s=open(sys.argv[3]).read(); a=s.index("ot_sram_1r1w_256x256_m2_r0c0_g256 u_mem("); b=s.index(".wd_in(w_d[b*256+:256])", a)
open(sys.argv[4],"w").write(s[:b]+".wd_in(w_d[b*256+:256]^256'd1)"+s[b+len(".wd_in(w_d[b*256+:256])"):])
PY
one() { seed=$1
  b() { iverilog -g2012 -DTB_SEED=$seed -DTB_CYC=${CYC:-4000} -DTB_MUT=$3 $2 -o $O/$1_$seed.vvp $E/tb_cp.sv $4 $5 $M && vvp -n $O/$1_$seed.vvp > $O/$1_$seed.log; }
  b ref "" 0 $LAND $LLR; b rw -DOT_HBM_RW_MACROS 0 $LAND $LLR
  b m_llr_addr -DOT_HBM_RW_MACROS 0 $LAND $O/mut_llr_addr.sv; b m_land_data -DOT_HBM_RW_MACROS 0 $O/mut_land_data.sv $LLR
  b m_mut -DOT_HBM_RW_MACROS 1 $LAND $LLR
  echo "seed $seed $(grep COVER $O/rw_$seed.log)"
  if [ -s $O/ref_$seed.log ] && cmp -s $O/ref_$seed.log $O/rw_$seed.log; then echo "seed $seed LOCKSTEP EQUAL ($(wc -l < $O/ref_$seed.log) lines)"; else echo "seed $seed LOCKSTEP DIFF FAIL"; fi
  for m in m_llr_addr m_land_data m_mut; do cmp -s $O/ref_$seed.log $O/${m}_$seed.log && echo "seed $seed $m SURVIVED FAIL" || echo "seed $seed $m killed"; done
}
for seed in 1 7 1103; do one $seed > $O/seed_$seed.txt 2>&1 & done; wait
cat $O/seed_*.txt; ! grep -q FAIL $O/seed_*.txt
