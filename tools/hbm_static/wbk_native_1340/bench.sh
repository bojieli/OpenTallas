#!/bin/bash
set -euo pipefail
ROOT=${WBK1340_RUN_ROOT:?immutable staged root}
cd "$ROOT/src"
mkdir -p "$ROOT/bench"
bash tools/hbm_static/wbk_native_1340/counterexample.sh "$ROOT/bench/counterexample" > "$ROOT/bench/counterexample.log" 2>&1
for c in wbq_e wbq_w wbq_e_wopen wbq_mut_quad wbq_mut_span wbq_mut_premature wbq_mut_ksaddr wbq_mut_slice wbq_mut_commit wbq_mut_credit wbq_mut_pp wbq_mut_lock; do
 bash rtl/hbm_accel/loader/service_native/run_stk_quadrant_bench.sh "$ROOT/bench/$c" "$c" > "$ROOT/bench/$c.log" 2>&1
 tail -2 "$ROOT/bench/$c.log"
done
printf 'WBK1340_EXISTING_WITNESSES_COMPLETE\n'
