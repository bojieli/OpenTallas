#!/bin/bash
# QW-COLL 10-19: regional split C + 4 Q behavioural benches + negative controls (Verilator 5.050, daemon-pinned).
set -u
D=${D:-/srv/opentallas-scratch/claude/qw-coll-split-1019}
O=${O:-$D/out}
cd "$D/src"
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
verilator --version
mkdir -p "$O"
B="python3 tools/qwen_coll_tp8_static_bench.py --split"
run() { n=$1; shift; ( $B --out "$O/$n" "$@" > "$O/$n.log" 2>&1; echo "RC $n $?" >> "$O/rc.txt" ) & }
run unit_u66      --latu 66 --lats 391
run prod_u66      --latu 66 --lats 391 --production
run prod_u65      --latu 65 --lats 390 --production
run mut_lead      --latu 66 --lats 391 --only 'reduce_8w_x16|gather_4w_x4' --mutant-define OT_COLL_SPLIT_MUT_LEAD
run mut_ex        --latu 66 --lats 391 --only 'reduce_8w_x16' --mutant-define OT_COLL_SPLIT_MUT_EX
run mut_rerr      --latu 66 --lats 391 --only 'fault_nan' --mutant-define OT_COLL_SPLIT_MUT_RERR
run mut_rank      --latu 66 --lats 391 --only 'reduce_8w_x16' --mutant-define OT_TP8S_MUT_RANK
run mut_rlat      --latu 66 --lats 391 --only 'reduce_8w_x16' --mutant-define OT_TP8S_MUT_RLAT
run mut_gather    --latu 66 --lats 391 --only 'gather_4w_x4' --mutant-define OT_TP8S_MUT_GATHER
run mut_sbank     --latu 66 --lats 391 --only 'reduce_8w_x16' --mutant-define OT_COLL_SPLIT_MUT_SBANK
wait
sort "$O/rc.txt"
for f in "$O"/*.log; do echo "== $f"; grep -E "^case |COLL_TP8S|build failed|%Error" "$f" | head -20; done
