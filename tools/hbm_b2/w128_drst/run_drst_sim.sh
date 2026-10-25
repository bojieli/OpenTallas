#!/bin/bash
set -uo pipefail
cd "$(dirname "$0")"; S=src; mkdir -p drst_sim; O=drst_sim
G=/srv/opentallas-scratch/claude/codex-hbm-hc-physical-1025/src/ot_hdc_v41x_hcp.sv   # pre-fix source (591bcf802)
awk '/^module ot_hdc_v41x_hcp_lanes/{p=1} p{print} p&&/^endmodule/{exit}' $G | sed 's/^module ot_hdc_v41x_hcp_lanes/module gold_hcp_lanes/' > $O/gold_lanes.sv
grep -q "DRST(ADRST)) u_mul" $S/ot_hdc_v41x_hcp.sv || { echo "fixed source missing"; exit 2; }
grep -q "DRST(ADRST)) u_mul" $O/gold_lanes.sv && { echo "gold is not pre-fix"; exit 2; }
F="$S/ot_hdc_prefix.sv $S/ot_hdc_fastfp.sv $S/ot_hdc_fp32_add_lat.sv $S/ot_hdc_fp32_mul_lat.sv $S/ot_hdc_v41x_hcp.sv $O/gold_lanes.sv"
for mode in gate MUT_VALID MUT_DATA; do
  D=""; X=""; [ $mode = MUT_VALID ] && { D="-DMUT_VALID"; X=mul_eq/mul_mv.sv; }; [ $mode = MUT_DATA ] && { D="-DMUT_DATA"; X=mul_eq/mul_md.sv; }
  iverilog -g2012 -DSYNTHESIS $D -s tb -o $O/$mode.vvp $F $X tb_drst.sv > $O/$mode.build.log 2>&1 || { echo "$mode BUILD FAIL"; tail -5 $O/$mode.build.log; continue; }
  vvp -n $O/$mode.vvp > $O/$mode.log 2>&1; echo "$mode: $(grep DRST_CHECK $O/$mode.log)"; grep -m2 MISMATCH $O/$mode.log
done
