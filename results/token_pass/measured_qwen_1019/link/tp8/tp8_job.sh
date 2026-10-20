#!/bin/bash
# TOKSIM-QW/LINK 10-19: TP8 collective co-sim on the qw-gen3 release RTL with the dv2f18dh2 GEN coll_lane_latency.json. usage: tp8_job.sh CASE ARGS...
set -u
cd "$(dirname "$0")"
export OT_VERILATOR=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
c=$1; shift
python3 tools/qwen_coll_tp8_static_links_bench.py --out out/$c "$@"; rc=$?
rm -rf out/$c/obj_*; echo "TP8_CASE $c rc=$rc"; exit $rc
