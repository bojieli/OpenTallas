#!/bin/bash
set -eu
out=$1
bash tools/qwen_tp8/vm_die_static_bench.sh "$out" -GMEM=1
ulimit -c 0
for mode in 1 2 3 4 5 6 7 8; do
    set +e
    "$out/obj/Vtb_qfd_vm_die_static" +COMMIT_MUT="$mode" > "$out/mutant$mode.log" 2>&1
    rc=$?
    set -e
    echo "MUTANT $mode exit=$rc"
    cat "$out/mutant$mode.log"
    test "$rc" != 0
    grep -q 'FAIL' "$out/mutant$mode.log"
done
