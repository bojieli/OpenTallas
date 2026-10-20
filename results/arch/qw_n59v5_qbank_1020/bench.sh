#!/bin/bash
set -uo pipefail
root=$(cd "$(dirname "$0")/../../.." && pwd)
unit=$1;run=$2;mkdir -p "$run"
export VERILATOR=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
export N59_RECV=1 N59_RECV_MUT=0 N59_QB_ALIGN=1 N59_QB_LOCAL32=1 N59_QB_LOCAL_MUT=0
export SPL_SOFF=3 SPL_BOFF=0 SPL_ROFF=4 SPLIT_ONLY=rnd_s1
expect=0
case "$unit" in
 default_rnd) N59_QB_LOCAL32=0;;
 local_rnd) :;;
 local_reset8) SPLIT_ONLY=rnd_reset8;;
 local_mu) SPLIT_ONLY=mu_ovl_positive;;
 local_dv) SPLIT_ONLY=dv_positive;;
 mut_mask) N59_QB_LOCAL_MUT=1;expect=1;;
 mut_select) N59_QB_LOCAL_MUT=2;expect=1;;
 *) exit 2;;
esac
bash "$root/rtl/test/qwen_split/run_native59_split_bench.sh" "$run" > "$run/wrapper.log" 2>&1
rc=$?
if [ "$expect" = 0 ]; then
 test "$rc" = 0 || { echo "N59LOCAL_FAIL $unit rc=$rc";exit 1; }
 echo "N59LOCAL_PASS $unit"
else
 test "$rc" != 0 && grep -q '^N59RND_FAIL' "$run/rnd_s1.log" || { echo "N59LOCAL_MUTANT_SURVIVED_OR_BUILD_FAIL $unit rc=$rc";exit 1; }
 echo "N59LOCAL_MUTANT_REJECTED $unit"
fi
