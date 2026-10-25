#!/bin/bash
# 3000-cycle variant of run_drst_sim.sh, the three modes in parallel
set -uo pipefail
cd "$(dirname "$0")"; S=src; O=drst_sim_3k; mkdir -p $O
cp drst_sim/gold_lanes.sv $O/
F="$S/ot_hdc_prefix.sv $S/ot_hdc_fastfp.sv $S/ot_hdc_fp32_add_lat.sv $S/ot_hdc_fp32_mul_lat.sv $S/ot_hdc_v41x_hcp.sv $O/gold_lanes.sv"
for mode in gate MUT_NORST MUT_DATA MUT_VALID; do (
  D=""; X=""; [ $mode = MUT_VALID ] && { D="-DMUT_VALID"; X=mul_eq/mul_mv.sv; }; [ $mode = MUT_DATA ] && { D="-DMUT_DATA"; X=mul_eq/mul_md.sv; }; [ $mode = MUT_NORST ] && D=-DMUT_NORST
  iverilog -g2012 -DSYNTHESIS $D -s tb -o $O/$mode.vvp $F $X tb_drst_3k.sv > $O/$mode.build.log 2>&1 || { echo "$mode BUILD FAIL"; exit; }
  vvp -n $O/$mode.vvp > $O/$mode.log 2>&1; echo "$mode: $(grep DRST_CHECK $O/$mode.log)"; grep -m2 MISMATCH $O/$mode.log ) &
done; wait
