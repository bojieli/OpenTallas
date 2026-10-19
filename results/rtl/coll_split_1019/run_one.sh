#!/bin/bash
# QW-COLL 10-19: one regional-split bench variant (Verilator 5.050, daemon-pinned). usage: run_one.sh NAME ARGS...
set -u
D=${D:-/srv/opentallas-scratch/claude/qw-coll-split-1019/v3}
cd "$D/src"
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
export OT_BENCH_J=${OT_BENCH_J:-4}
n=$1; shift
mkdir -p "$D/out"
verilator --version > "$D/out/$n.log"
python3 tools/qwen_coll_tp8_static_bench.py --split --out "$D/out/$n" "$@" >> "$D/out/$n.log" 2>&1
rc=$?
echo "RC $n $rc" | tee -a "$D/out/$n.log"
grep -E "^case |COLL_TP8S|build failed|%Error" "$D/out/$n.log" | head -30
exit $rc
