#!/bin/bash
# run_bench.sh <outdir> [mut]   (cwd = repo root): RFETCH=1 vs RFETCH=0 lockstep of ot_hcoll_port; mut = late-fetch mutant.
set -u; O=$1; M=${2:-}; mkdir -p $O; D=physical/variant_fill/hcoll_port_rfetch_f9
DEF=""; [ "$M" = mut ] && DEF=-DOT_HCOLL_MUT_RFETCH_LATE
iverilog -g2012 $DEF -s tb_hcoll_rfetch -o $O/tb$M.vvp rtl/hbm_accel/ha2_ar/ot_ha2_prims.sv \
  physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v rtl/hbm_accel/tu/ot_hcoll_sram_prims.sv \
  rtl/hbm_accel/tu/ot_hcoll_port.sv $D/tb_hcoll_rfetch.sv > $O/build$M.log 2>&1 || { echo "BUILD FAILED"; cat $O/build$M.log; exit 3; }
vvp $O/tb$M.vvp > $O/run$M.log 2>&1; grep -E "^HCOLL_RFETCH|^MISMATCH|^FAIL" $O/run$M.log | head -8
grep -q '^HCOLL_RFETCH PASS' $O/run$M.log
