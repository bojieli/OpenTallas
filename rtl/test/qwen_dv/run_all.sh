#!/bin/bash
# Q-DV slice benches: positive run (all five must PASS) and one negative control per bench (must FAIL).
# Usage: rtl/test/qwen_dv/run_all.sh [WORK]   (Verilator; ~6-10 min build per MUT variant, seconds per bench)
set -u
D=$(cd "$(dirname "$0")" && pwd); WORK=${1:-/tmp/qdv_bench}
python3 "$D/dv_bench.py" a b c d e --work "$WORK"; pos=$?
declare -A M=([1]=a [2]=b [3]=c [4]=d [5]=e)
for m in 1 2 3 4 5; do python3 "$D/dv_bench.py" ${M[$m]} --mut $m --work "$WORK" > "$WORK/mut$m.out" 2>&1 & done
wait; neg=0
for m in 1 2 3 4 5; do cat "$WORK/mut$m.out"; grep -q "MUT=$m: FAIL" "$WORK/mut$m.out" || { echo "MUTANT $m NOT CAUGHT"; neg=1; }; done
[ $pos -eq 0 ] && [ $neg -eq 0 ] && echo "QDV BENCHES: PASS (5 positive, 5 mutants failed)" || { echo "QDV BENCHES: FAIL"; exit 1; }
