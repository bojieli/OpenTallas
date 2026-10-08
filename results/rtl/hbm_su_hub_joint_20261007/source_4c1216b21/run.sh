#!/bin/bash
set -u
mode=$1
base=/srv/opentallas-scratch2/scratch/codex/hbm-su-hub-4c1216b21
cd "$base/src-$mode" || exit 2
export OT_VFLAGS='--unroll-count 4 -fno-dfg'
if [ "$mode" = neg ]; then export OT_VFLAGS="$OT_VFLAGS +define+OT_NEG_RED_NOLOCK"; fi
python3 tools/hbm_su_c12.py campaign --ctl12 2 --ropi 1 --rout 2 --rkc 1 --rhalf 1 --rhpar 1 --gsh 1 --kimm 1 --denr 1 --dring 2 --quick --only random --no-1024 --scratch "$base/work-$mode" --out "$base/$mode.json" > "$base/$mode.log" 2>&1
rc=$?
printf '%s\n' "$rc" > "$base/$mode.rc"
exit "$rc"
