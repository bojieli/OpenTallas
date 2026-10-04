#!/bin/bash
cd /tmp/ha3-clock-0554f2ea0/src
~/bin/admit.sh 1 -- python3 tools/hbm_accel_epilogue_clock_gate.py --origin-commit 0554f2ea02eec3f0cc1fe3c28b31943b914b0d88 --work /tmp/ha3-clock-0554f2ea0/work --out /tmp/ha3-clock-0554f2ea0/result.json
rc=$?
printf %s
 "$rc" > /tmp/ha3-clock-0554f2ea0/exit
exit "$rc"
