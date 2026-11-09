#!/bin/bash
set -u
B=/srv/opentallas-scratch3/claude/type-safe-3b
cd $B/src_s81p
P=physical/die_plan/s81/plan_h2_2249.json
prlimit --as=72000000000 python3 -I -B tools/die_plan/bind.py bind $P --asbuilt $B/s81p/asbuilt_ts3.json --out $B/s81p/bind --strict > $B/s81p/bind.log 2>&1
echo BIND rc=$?
tail -3 $B/s81p/bind.log | cut -c1-300
cd $B
python3 -I -B $B/tools/die_plan/ts_relay_miter.py $B/src_s81p/$P $B/s81p/s81_v3b_ts3_event.json $B/s81_cbind3b_rtl $B/s81p/bind/rtl $B/s81p/miter.json; echo MITER rc=$?
python3 -I - <<P
import json
d=json.load(open("$B/s81p/bind/bind_report.json"));print("n_errors",d.get("n_errors"))
print(open("$B/s81p/miter.json").read()[:800])
P
