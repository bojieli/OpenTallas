#!/usr/bin/env bash
# Run via ot-run from a source-pinned staged directory.
set -euo pipefail
OUT=$(realpath -m "$1"); mkdir -p "$OUT"
HERE=$(cd "$(dirname "$0")" && pwd)
bash "$HERE/run_pring_static_bench.sh" "$OUT/positive"
rc=0
"$OUT/positive/obj/Vtb_hgi_coll_pring_static" +fault=9 > "$OUT/compiler-collision.log" 2>&1 || rc=$?
if [[ "$rc" == 0 ]] || ! grep -q 'compiler injection collision' "$OUT/compiler-collision.log"; then
 echo "STATIC_RING SUITE FAIL compiler collision rc=$rc";exit 1
fi
echo 'STATIC_RING COMPILER COLLISION PASS'
for mutant in dropcarry tag ringorder; do
 case "$mutant" in
  dropcarry) arg=-GMUT_CARRY=1; pattern='golden mismatch';;
  tag) arg=-GMUT_TAG=1; pattern='unexpected schedule fault cycle10';;
  ringorder) arg=-GMUT_RING_ORDER=1; pattern='golden mismatch';;
 esac
 rc=0
 bash "$HERE/run_pring_static_bench.sh" "$OUT/$mutant" "$arg" || rc=$?
 # The runner reserves rc2 for a build failure. Only an executed failing DUT
 # with the intended reason establishes mutant sensitivity.
 if [[ "$rc" != 1 ]] || ! grep -q "$pattern" "$OUT/$mutant/run.log"; then
  echo "STATIC_RING SUITE FAIL mutant=$mutant rc=$rc";exit 1
 fi
 echo "STATIC_RING MUTANT PASS $mutant"
done
echo 'STATIC_RING SUITE PASS'
