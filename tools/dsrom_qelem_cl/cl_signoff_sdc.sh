#!/bin/bash
# Sign-off post-SDC of the PQ q-element (closure loop, 2026-10-06), read after the route's 6_final.sdc (period 0.833,
# setup uncertainty 163 ps, inputs 624 / 360 ps, outputs -193 / -322 ps):
#   setup uncertainty 60 ps (the 0.833 sign-off), max input delay 727 ps (= 833 - 106: the pin -> flop budget of every
#   q route since Z22), outputs at the CALIBRATED insertion per physical/abi3/dsrom_qy_elem_io.sdc's derivation (a sibling
#   q-element's boundary register captures them: max = 360 ps external - its SS insertion, min = - its FF insertion;
#   sta_cal_io.tcl used the routed b_go, the loop gives the calibrated boundary-register mean CK_SS_MEAN / CK_FF_MEAN).
# usage (cwd = source tree): CK_SS_MEAN=.. CK_FF_MEAN=.. cl_signoff_sdc.sh  -> physical/abi3/gen/dsrom_q_cl_signoff.sdc
set -e
: "${CK_SS_MEAN:?calibrated SS insertion (ps)}" "${CK_FF_MEAN:?calibrated FF insertion (ps)}"
mkdir -p physical/abi3/gen
python3 - "$CK_SS_MEAN" "$CK_FF_MEAN" > physical/abi3/gen/dsrom_q_cl_signoff.sdc <<'PY'
import sys
ss, ff = float(sys.argv[1]), float(sys.argv[2])
print(f"# PQ q-element sign-off post-SDC (cl_signoff_sdc.sh): CK_SS_MEAN {ss:.1f} ps, CK_FF_MEAN {ff:.1f} ps")
print("set_clock_uncertainty -setup 60 [get_clocks core_clk]")
print("set_input_delay -max 727 -clock core_clk [all_inputs -no_clocks]")
print(f"set_output_delay -max {360.0 - ss:.1f} -clock core_clk [all_outputs]")
print(f"set_output_delay -min {-ff:.1f} -clock core_clk [all_outputs]")
PY
cat physical/abi3/gen/dsrom_q_cl_signoff.sdc
