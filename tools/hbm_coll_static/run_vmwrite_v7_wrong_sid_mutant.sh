#!/bin/bash
# Expected to fail: a real sid1 master installed in the sid0 production binding.
set -euo pipefail
HERE=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
ROOT=$(cd -- "$HERE/../.." && pwd)
BUILD=${1:?usage: run_vmwrite_v7_wrong_sid_mutant.sh BUILD}
mkdir -p "$BUILD"
BASE="$ROOT/rtl/hbm_accel/generic/collective/p2p"
iverilog -g2012 -s tb_hgi_coll_static_vmwrite -o "$BUILD/sim.vvp" \
 "$BASE/ot_hgi_coll_static_vmwrite_roots_v6.sv" \
 "$BASE/ot_hgi_coll_static_vmwrite_roots_v7_sid.sv" \
 "$ROOT/results/rtl/hbm_writer_v7_sid_0430/proof/tb_wrong_sid0.sv"
vvp "$BUILD/sim.vvp"
