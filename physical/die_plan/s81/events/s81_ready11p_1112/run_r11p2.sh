#!/bin/bash
W=/srv/opentallas-scratch2/claude/s87bind; SRC=$W/bsrc3_r11p; AB=$W/asbuilt_f_s87p2.json; OUT=$W/out_r11p2; P=physical/die_plan/s81/plan_h2_2249.json
cd "$SRC" || exit 2
export PYTHONDONTWRITEBYTECODE=1
echo "start $(date) plan $(sha256sum < $P | cut -c1-12) (elab copied from out_r11p; bind only)" > $W/bind_r11p2.run
[ -d $OUT ] || cp -a $W/out_r11p $OUT || exit 3
/usr/bin/time -v prlimit --as=100000000000 nice -n 5 python3 -I -B tools/die_plan/bind.py bind $P --asbuilt $AB --out $OUT --strict > $W/bind_r11p2.log 2>&1
rc=$?
echo "BIND rc=$rc $(date) $(grep -E 'Error|ERROR|ResetError|BindError' $W/bind_r11p2.log | head -1 | cut -c1-500)" >> $W/bind_r11p2.run
exit $rc
