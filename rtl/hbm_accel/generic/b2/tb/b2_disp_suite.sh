#!/bin/bash
# exact (3 seeds) + mutants: DMUT 1 slice bit, RMUT 2 station ordering, DMUT 3 early retire.  run from the repo root.
O=${1:-/tmp/b2disp}; R=rtl/hbm_accel/generic/b2/tb/run_b2_disp.sh
for s in 1 2 3; do echo "exact seed $s: $($R $O ex$s 0 0 4000 $s | head -1)"; done
echo "mut slice (DMUT1): $($R $O m1 1 0 4000 1 | head -1)"
echo "mut order (RMUT2): $($R $O m2 0 2 4000 1 | head -1)"
echo "mut retire (DMUT3): $($R $O m3 3 0 4000 1 | head -1)"
