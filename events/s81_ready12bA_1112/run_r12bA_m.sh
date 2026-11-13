#!/bin/bash
O=/srv/opentallas-scratch2/claude/s81-leaf-floor-2; SRC=$O/bsrc_r12bA_m; AB=$O/asbuilt_lfcs_m.json; OUT=$O/out_r12bA_m; P=physical/die_plan/s81/plan_r12bA3.json
export PYTHONDONTWRITEBYTECODE=1
bash $O/bin/mktrees2.sh || exit 2
cd $SRC || exit 9
echo "plan $(sha256sum < $P | cut -c1-12) tools $(cd /srv/opentallas-scratch2/claude/wt/s81-lfcs-merge && git rev-parse --short HEAD)"
rm -rf $O/r12b/g0m2
(nice -n 10 python3 -I tools/die_plan/check.py $SRC/$P --out $O/r12b/g0m2 --quiet > $O/r12b/g0m2.log 2>&1; echo G0_RC=$? >> $O/r12b/g0m2.log) &
prlimit --as=100000000000 nice -n 5 python3 -I -B tools/die_plan/bind.py elab $P --asbuilt $AB --out $OUT --mem 48 > $O/r12b/elab_m.log 2>&1; r=$?; echo ELAB_RC=$r
[ $r = 0 ] && { prlimit --as=100000000000 nice -n 5 python3 -I -B tools/die_plan/bind.py bind $P --asbuilt $AB --out $OUT --strict > $O/r12b/bind_m.log 2>&1; echo BIND_RC=$?; }
wait; grep -v TAP-RAD $O/r12b/g0m2.log | tail -1
