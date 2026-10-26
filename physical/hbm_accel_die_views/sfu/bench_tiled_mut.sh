#!/bin/bash
# hbm-phys-1010 [sfu]: the closure loop's expect=FAIL bench for the tiled SFU: the committed rtl_tiled quarter with ONE
# tile mutant (MUT = ROT | TAP | ACC, default ACC: lane output bit 0 dropped from the accumulate) must mismatch the
# reference; exits non-zero (and prints SFU_TILED_MUT_CAUGHT) when the bench catches it.
#   bench_tiled_mut.sh <outdir> [ROT|TAP|ACC]   (run in the source root)
set -u; O=$1; M=${2:-ACC}; mkdir -p $O; R=physical/hbm_accel_die_views/sfu/rtl_tiled
cp $R/tb_hfd_sfu.sv $R/hfd_sfu.sv $R/hfd_sfu_tile.sv $R/ot_su12_sfu_simstub.sv $R/tb_in.mem $R/tb_out.mem $O/
cd $O && iverilog -g2012 -DOT_SFU_TILE_MUT_$M -o sim_mut tb_hfd_sfu.sv hfd_sfu.sv hfd_sfu_tile.sv ot_su12_sfu_simstub.sv \
  || { echo "SFU_TILED_MUT_BUILD_FAIL"; exit 0; }
vvp -n sim_mut > mut.log 2>&1; rc=$?
grep OT_RESULT mut.log
if [ $rc != 0 ] && grep -q "mismatches=[1-9]" mut.log; then echo "SFU_TILED_MUT_CAUGHT mut=$M"; exit 1; fi
echo "SFU_TILED_MUT_NOT_CAUGHT mut=$M"; exit 0
