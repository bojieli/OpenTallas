#!/bin/bash
# KV-SAFE32D 10-20 (route B K budget 104): behavioural benches + mutant witnesses of the ECTL frame qkd_ectl3_kiss_st at the DIE configuration
# (RESPONSE_LAT 104 / QK_ISSUE_AGE 115), Verilator 5.050, all cases in parallel.  usage (fleet): kv_safe32d_bench.sh COMMIT
set -uo pipefail
C=$1
B=/srv/opentallas-scratch/claude/kv-safe32d
W=$B/wt-$C; R=$B/bench-$C
M=/srv/opentallas-scratch/claude/git-mirror/OpenTallas.git
GH=https://github.com/bojieli/OpenTallas
mkdir -p $R
if [ ! -d $W ]; then git -C $M fetch -q $GH claude/kv-safe32d-1020; git -C $M worktree add --detach $W $C; fi
cd $W
[ "$(git rev-parse --short=9 HEAD)" = $C ] || { echo "wrong commit"; exit 2; }
K=tools/qwen_static_kv/ectl_kiss_st_k_bench.sh; L=tools/qwen_static_kv/ectl_st_bench.sh
run() { local n=$1; shift; ( "$@" > $R/$n.log 2>&1; echo "rc=$?" >> $R/$n.log ) & }
run k_pass        env RL=104 QK=115 bash $K $R/k_pass 0
run k_mut5_layer  env RL=104 QK=115 bash $K $R/k_mut5 5
run k_mut8_late   env RL=104 QK=115 bash $K $R/k_mut8 8
run k_mut9_qkm1   env RL=104 QK=115 bash $K $R/k_mut9 9
run k_rule_qk114  env RL=104 QK=114 bash $K $R/k_qk114 0
run k_unit_2_34   env RL=2 QK=34 bash $K $R/k_unit 0
run l_pass        env RL=104 QK=115 bash $L $R/l_pass 0
run l_mut1        env RL=104 QK=115 bash $L $R/l_mut1 1
run l_mut2        env RL=104 QK=115 bash $L $R/l_mut2 2
wait
for f in $R/*.log; do echo "== $(basename $f .log): $(grep -E '^(PASS|FAIL)' $f | tail -1) $(tail -1 $f)"; done | tee $R/SUMMARY.txt
