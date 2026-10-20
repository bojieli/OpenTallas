#!/bin/bash
set -euo pipefail
export VERILATOR=/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator
export OT_GQ_P192=1 OT_GQ_N32=1 JOBS=8
for mode in ia1 slot dep iaign;do
 bash rtl/hbm_accel/generic/collective/p2p/run_coll_gq_ia.sh "$PWD/bench_r6_ia/$mode" "$mode"
done
echo GQ_R6_IA74_PASS_POSITIVE3MUTANTS
