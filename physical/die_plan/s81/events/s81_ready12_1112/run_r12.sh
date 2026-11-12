#!/bin/bash
W=/srv/opentallas-scratch2/claude/s87bind; SRC=$W/bsrc4_r12; AB=$W/asbuilt_f_s87r12.json; OUT=$W/out_r12; P=physical/die_plan/s81/plan_h2_2249.json
cd "$SRC" || exit 2
export PYTHONDONTWRITEBYTECODE=1
echo "start $(date) plan $(sha256sum < $P | cut -c1-12)" > $W/bind_r12.run
prlimit --as=100000000000 nice -n 5 python3 -I -B tools/die_plan/bind.py elab $P --asbuilt $AB --out $OUT --mem 48 > $W/elab_r12.log 2>&1; r=$?
echo "ELAB rc=$r $(date)" >> $W/bind_r12.run; [ $r = 0 ] || exit 1
/usr/bin/time -v prlimit --as=100000000000 nice -n 5 python3 -I -B tools/die_plan/bind.py bind $P --asbuilt $AB --out $OUT --strict > $W/bind_r12.log 2>&1
rc=$?
echo "BIND rc=$rc $(date) $(grep -E "Error|ERROR|ResetError|BindError" $W/bind_r12.log | head -1 | cut -c1-500)" >> $W/bind_r12.run
exit $rc
