#!/bin/bash
# usage: run_formal.sh W H DEPTH MUTT MUTR BEATS -> bounded yosys sat miter (reference delayed vs TX->H stations->RX under premises P1/P2).
# Needs docker + an image with yosys (IMG, default opentallas/orfs:asap7lock-grtT3). Run under nice + systemd-run MemoryMax=48G.
set -u
W=$1; H=$2; N=$3; MT=${4:-0}; MR=${5:-0}; BE=${6:-2}
D=$(cd "$(dirname "$0")" && pwd); R=$D/../..; IMG=${IMG:-opentallas/orfs:asap7lock-grtT3}
O=$(mktemp -d); cp $R/rtl/common/ot_bus_gear.sv $R/rtl/hbm_accel/generic/transport/ot_hbm_hw_lane.sv $D/hw_miter.sv $O/
cat > $O/m.ys <<YS
read_verilog -sv -formal /w/ot_bus_gear.sv /w/ot_hbm_hw_lane.sv /w/hw_miter.sv
chparam -set W $W -set H $H -set BEATS $BE -set MUTT $MT -set MUTR $MR hw_miter
hierarchy -top hw_miter
proc; flatten; opt_clean; memory_map; opt -fast; async2sync
sat -seq $N -set-init-zero -prove-asserts -verify -show-inputs -timeout 1500
YS
docker run --rm --memory=48g -v $O:/w -w /w $IMG yosys -q -l /w/m.log /w/m.ys >/dev/null 2>&1
if grep -q "SUCCESS" $O/m.log; then echo "FORMAL W=$W H=$H depth=$N BEATS=$BE MUTT=$MT MUTR=$MR: PROVEN (bounded, no counterexample in $N cycles)";
elif grep -q "FAIL" $O/m.log; then echo "FORMAL W=$W H=$H depth=$N BEATS=$BE MUTT=$MT MUTR=$MR: COUNTEREXAMPLE"; else echo "FORMAL W=$W H=$H: INCONCLUSIVE"; fi
rm -rf $O
