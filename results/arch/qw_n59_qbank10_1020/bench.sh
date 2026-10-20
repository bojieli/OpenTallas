#!/bin/bash
# QW-CB16A0-3 10-20: qbank10 (QB_STAGE=1 QB_M546=1) lockstep units vs the flat r1 reference (split bench), Verilator 5.050.
# Offsets: qbank10 = qbank9 + 1 input edge + 1 output edge => SOFF 5 (service ports), BOFF 0 (bank ports), ROFF 6;
# the random bench probes bank internals at BOFF + 1 + QB_STAGE.
set -uo pipefail
root=$(cd "$(dirname "$0")/../../.." && pwd)
unit=$1;run=$2;mkdir -p "$run"
export VERILATOR=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
export N59_RECV=1 N59_RECV_MUT=0 N59_QB_ALIGN=1 N59_QB_LOCAL32=1 N59_QB_LOCAL_MUT=0 N59_QB_STAGE=1 N59_QB_M546=1
export SPL_SOFF=${SPL_SOFF:-5} SPL_BOFF=${SPL_BOFF:-0} SPL_ROFF=${SPL_ROFF:-6} SPLIT_ONLY=rnd_s1
expect=0; log=rnd_s1
case "$unit" in
 rnd) :;;
 rnd_s2) SPLIT_ONLY=rnd_s2; log=rnd_s2;;
 reset8) SPLIT_ONLY=rnd_reset8; log=rnd_reset8;;
 mu) SPLIT_ONLY=mu_ovl_positive; log=mu_ovl_positive;;
 dv) SPLIT_ONLY=dv_positive; log=dv_positive;;
 q9_rnd) N59_QB_STAGE=0 N59_QB_M546=0 SPL_SOFF=3 SPL_BOFF=0 SPL_ROFF=4;;
 m546_only) N59_QB_STAGE=0 SPL_SOFF=3 SPL_BOFF=0 SPL_ROFF=4;;
 mut_old_offsets) SPL_SOFF=3 SPL_BOFF=0 SPL_ROFF=4; expect=1;;
 mut_qb1) SPLIT_ONLY=rnd_qb1_unreg; log=rnd_qb1_unreg; expect=2;;
 mut_mask) N59_QB_LOCAL_MUT=1; expect=1;;
 mut_select) N59_QB_LOCAL_MUT=2; expect=1;;
 *) exit 2;;
esac
bash "$root/rtl/test/qwen_split/run_native59_split_bench.sh" "$run" > "$run/wrapper.log" 2>&1
rc=$?
if [ "$expect" = 0 ]; then
 test "$rc" = 0 || { echo "N59QB10_FAIL $unit rc=$rc"; tail -5 "$run/wrapper.log"; exit 1; }
 echo "N59QB10_PASS $unit"
elif [ "$expect" = 2 ]; then
 grep -q "OK (mutant fails)" "$run/wrapper.log" || { echo "N59QB10_MUTANT_SURVIVED_OR_BUILD_FAIL $unit rc=$rc"; exit 1; }
 echo "N59QB10_MUTANT_REJECTED $unit"
else
 test "$rc" != 0 && grep -q '^N59RND_FAIL' "$run/$log.log" || { echo "N59QB10_MUTANT_SURVIVED_OR_BUILD_FAIL $unit rc=$rc";exit 1; }
 echo "N59QB10_MUTANT_REJECTED $unit"
fi
