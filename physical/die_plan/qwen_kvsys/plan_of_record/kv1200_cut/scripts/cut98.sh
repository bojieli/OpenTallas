#!/bin/bash
# DIE-KV-98: DIE-KV-97 cut.sh with paths for epyc4 (tree in /dev/shm/dkv98/main). usage: cut98.sh OUTDIR "DELTA@SHEET@APPLIER@DELTA_BASE_PLAN" ...
set -euo pipefail
cd /
S=/srv/opentallas-scratch2/claude; O=/dev/shm/dkv98/kvcut; M=/dev/shm/dkv98/main; OUT=$1; shift
B=$(readlink -f $S/kw43/kvr2)
rm -rf $OUT; cp -al $B $OUT; rm $OUT/plan_c.json
cd $M
nice -n 19 python3 -I $O/compose_cut.py $B/plan_c.json $OUT/step0.json $O/ev \
  --types-from $S/kv-plan-2/plan_e2s2/plan_c.json=* --types-from $S/kv-plan-2/plan_kvfix1/plan_c.json=* \
  --types-from $S/kw43/kvrs/plan_c.json=*
cp $OUT/step0.json.report.json $OUT/compose_report.json
cur=$OUT/step0.json; n=0
for spec in "$@"; do
  IFS=@ read -r d sheet app dbase <<< "$spec"
  [ -f "$sheet" ] || { echo "NO INTENT SHEET for $d (scored, not adopted)"; exit 3; }
  n=$((n+1)); python3 -I $O/rebase_delta.py "$dbase" "$cur" "$d" $OUT/rb_$n.json
  (cd $OUT && python3 -I "$app" "$cur" $OUT/rb_$n.json $OUT/step$n.json)
  cur=$OUT/step$n.json
done
cp $cur $OUT/plan_c.json
python3 -I $O/eq_diff.py $OUT/step0.json $OUT/plan_c.json > $OUT/eq_diff.txt || true
cat $OUT/eq_diff.txt
nice -n 19 python3 -I tools/die_plan/check.py $OUT/plan_c.json --out $OUT/g0 > $OUT/g0.log 2>&1 || true
tail -1 $OUT/g0.log | cut -c1-300
python3 -I $O/g0_new.py $O/g0_base $OUT/g0 | tee $OUT/g0_new.txt
md5sum $OUT/plan_c.json; sha256sum $OUT/plan_c.json
