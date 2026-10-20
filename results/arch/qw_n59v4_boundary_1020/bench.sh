#!/bin/bash
set -uo pipefail
root=$(cd "$(dirname "$0")/../../.." && pwd)
case=$1
run=$2
mkdir -p "$run"
export VERILATOR=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
export N59_RECV=1 SPL_SOFF=3 SPL_BOFF=0 SPL_ROFF=4 N59_RECV_MUT=0 SPLIT_ONLY=rnd_s1
expect=0
case "$case" in
 base_rnd) N59_RECV=0;SPL_ROFF=3;;
 recv_rnd) :;;
 recv_mu) SPLIT_ONLY=mu_ovl_positive;;
 recv_dv) SPLIT_ONLY=dv_positive;;
 mut_bypass) N59_RECV_MUT=1;expect=1;;
 mut_late) N59_RECV_MUT=2;expect=1;;
 *) exit 2;;
esac
bash "$root/rtl/test/qwen_split/run_native59_split_bench.sh" "$run" > "$run/wrapper.log" 2>&1
rc=$?
if [ "$expect" = 0 ]; then
 test "$rc" = 0 || { echo "BOUNDARY_FAIL $case rc=$rc";exit 1; }
 echo "BOUNDARY_PASS $case"
else
 test "$rc" != 0 && grep -q '^N59RND_FAIL' "$run/rnd_s1.log" || { echo "BOUNDARY_MUTANT_SURVIVED_OR_BUILD_FAIL $case rc=$rc";exit 1; }
 echo "BOUNDARY_MUTANT_REJECTED $case"
fi
