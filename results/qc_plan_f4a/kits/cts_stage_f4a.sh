#!/bin/bash
# QC-PLAN-F4A CTS+GRT stage (task 4): install the plan spec computed on THIS kit's MIF0 placement (regate_placed.sh ->
# placed/<n>_placed_g4c.tcl, no measured input) as mscts_spec_f4a.tcl, append the CTS block (prog_m0 MIF0 lineage hooks),
# then the caller runs cts_m0.sh via ot-run.  usage: cts_stage_f4a.sh KITHOST KITROOT
set -euo pipefail
H=$1; KR=$2
W=$(cd "$(dirname "$0")/../../.." && pwd); P=$W/results/qc_plan_f4a/placed
for m in qfd_dv_s8x_vmr qfd_dv_s8_crh_rp1; do
  n=$([ $m = qfd_dv_s8x_vmr ] && echo vmr || echo rp1); K=$KR/${m}_f4a
  grep -q "VERDICT PASS" $P/${n}_placed_g4c.log || { echo "$n placed gate not PASS -- no CTS"; continue; }
  scp -q -o ControlPath=none $P/${n}_placed_g4c.tcl $H:$K/mscts_spec_f4a.tcl
  ssh -o ControlPath=none $H "cd $K && grep -q 'QC-PLAN-F4A CTS' config.mk || cat >> config.mk <<'CFG'

# ---- QC-PLAN-F4A CTS+GRT stage: mscts_spec_f4a.tcl = f4_g4c plan spec computed on this kit's MIF0 placement geometry
# (placed gate PASS, no measured input); TritonCTS off, ITERS 0 (report only); prog_m0 MIF0 hooks.  No DRT.
export PRE_CTS_TCL = /work/pre_cts_m0.tcl
override export POST_CTS_TCL = /work/post_cts_s5.tcl
override export POST_GLOBAL_ROUTE_TCL = /work/post_grt_s5.tcl
export OT_MSCTS_SPEC = /work/mscts_spec_f4a.tcl
CFG
md5sum mscts_spec_f4a.tcl config.mk"
done
