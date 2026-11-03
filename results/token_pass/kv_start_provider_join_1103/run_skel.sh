#!/bin/bash
# DIE-KV-63/start: build + run the START-skeleton vehicle (both modes).
set -uo pipefail
W=/srv/opentallas-scratch2/claude/die-kv-63-start; V=/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator
cd $W; rm -rf obj
/usr/bin/time -v $V --binary --timing -j 8 -Wno-fatal -Wno-lint -Wno-style --top-module tb --Mdir $W/obj -f $W/files.f > $W/build.log 2>&1
echo "BUILD_RC $?"; tail -3 $W/build.log
for m in 0 1; do $W/obj/Vtb +MODE=$m > $W/mode$m.log 2>&1; echo "RUN$m rc $?"; grep -E "VERDICT|BOOT|HUBWI|CLAND|PST rose|PST_NEVER" $W/mode$m.log | head -20; done
