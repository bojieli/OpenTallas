#!/bin/bash
# run_bench.sh <outdir> [mut]   (cwd = repo root): ot_hcoll_port RBSEL=1 K=9 vs the RFETCH line; mut = late bank select.
set -u; O=$1; M=${2:-}; mkdir -p $O; D=physical/variant_fill/hcoll_port_rbsel_idleA
DEF=""; [ "$M" = mut ] && DEF=-DOT_HCOLL_MUT_RBSEL
iverilog -g2012 $DEF -s tb_hcoll_rbsel -o $O/tb$M.vvp rtl/hbm_accel/ha2_ar/ot_ha2_prims.sv \
  physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v rtl/hbm_accel/tu/ot_hcoll_sram_prims.sv \
  rtl/hbm_accel/tu/ot_hcoll_port.sv $D/tb_hcoll_rbsel.sv > $O/build$M.log 2>&1 || { echo "BUILD FAILED"; cat $O/build$M.log; exit 3; }
vvp $O/tb$M.vvp > $O/run$M.log 2>&1; grep -E "^HCOLL_RBSEL|^MISMATCH|^SB_ERR|^FAIL" $O/run$M.log | head -12
grep -q '^HCOLL_RBSEL PASS' $O/run$M.log
