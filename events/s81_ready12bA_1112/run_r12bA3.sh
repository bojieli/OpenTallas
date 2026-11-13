#!/bin/bash
# ready12b-A without REACH-FIX-2 (B1-B3): G0 + strict bind (elab reused from out_r12bA, same as-built)
O=/srv/opentallas-scratch2/claude/s81-leaf-floor-2; SRC=$O/bsrc_r12ng_lfcs; AB=$O/asbuilt_lfcs.json; P=physical/die_plan/s81/plan_r12bA3.json
export PYTHONDONTWRITEBYTECODE=1
cp $O/r12b/s3_band.json $SRC/$P.new && mv $SRC/$P.new $SRC/$P
rm -rf $O/out_r12bA3; mkdir -p $O/out_r12bA3; cp -a $O/out_r12bA/. $O/out_r12bA3/; rm -rf $O/out_r12bA3/rtl $O/out_r12bA3/bind_report.json
cd $SRC || exit 9
echo "plan $(sha256sum < $P | cut -c1-12)"
rm -rf $O/r12b/g0a3
(cd $O/r12b/main26c9 && nice -n 10 python3 -I tools/die_plan/check.py $SRC/$P --out $O/r12b/g0a3 --quiet > $O/r12b/g0a3.log 2>&1; echo G0_RC=$? >> $O/r12b/g0a3.log) &
prlimit --as=100000000000 nice -n 5 python3 -I -B tools/die_plan/bind.py bind $P --asbuilt $AB --out $O/out_r12bA3 --strict > $O/r12b/bind_a3.log 2>&1; echo BIND_RC=$?
wait; grep -v TAP-RAD $O/r12b/g0a3.log | tail -1
