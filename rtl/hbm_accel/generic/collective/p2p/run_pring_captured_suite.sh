#!/usr/bin/env bash
# Execute only under ot-run resource admission from a pinned source archive.
set -euo pipefail
OUT=$(realpath -m "$1");mkdir -p "$OUT"
HERE=$(cd "$(dirname "$0")" && pwd)
bash "$HERE/run_pring_captured_bench.sh" "$OUT/positive"
rc=0
"$OUT/positive/obj/Vtb_hgi_coll_pring_captured_static" +fault=9 > "$OUT/compiler-collision.log" 2>&1 || rc=$?
if [[ "$rc" == 0 ]] || ! grep -q 'compiler injection collision' "$OUT/compiler-collision.log";then exit 1;fi
echo 'CAPTURED_RING COMPILER COLLISION PASS'
for mutant in dropcarry tag ringorder readlead;do
 case "$mutant" in
  dropcarry) arg=-GMUT_CARRY=1;pattern='golden mismatch';;
  tag) arg=-GMUT_TAG=1;pattern='unexpected schedule fault cycle5';;
  ringorder) arg=-GMUT_RING_ORDER=1;pattern='unexpected schedule fault';;
  readlead) arg=-GMUT_READ_LEAD=1;pattern='unexpected schedule fault cycle3';;
 esac
 rc=0
 bash "$HERE/run_pring_captured_bench.sh" "$OUT/$mutant" "$arg" || rc=$?
 if [[ "$rc" == 0 || "$rc" == 2 || "$rc" == 137 ]] || ! grep -q "$pattern" "$OUT/$mutant/run.log";then
  echo "CAPTURED_RING SUITE FAIL mutant=$mutant rc=$rc";exit 1
 fi
 echo "CAPTURED_RING MUTANT PASS $mutant"
done
echo 'CAPTURED_RING SUITE PASS'
