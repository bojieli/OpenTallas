#!/bin/bash
# TOKj-KV 10-23: run the KV die-slice vehicle (built by build.sh) on one boot image: nominal + the frame mutant.
#   run.sh OBJDIR IMGDIR OUT [MUT_FRAME]     IMGDIR holds frames.hex expect.txt epoch.txt (bench/boot_frames.py)
set -u
B=$(readlink -f $1)/obj/Vtb_kvslice; I=$(readlink -f $2); O=$(mkdir -p $3 && readlink -f $3); MF=${4:-}
EP=$(cat $I/epoch.txt)
BOOT_ARGS=()
[ "$(cat "$(dirname "$B")/../native_boot.profile" 2>/dev/null || echo 0)" = 0 ] || BOOT_ARGS+=(+START_AFTER_SETUP)
run() { local n=$1; shift; mkdir -p $O/$n; if [ -n "${KV_DCAL_VIAMAP:-}" ]; then python3 -I "$(dirname "$0")/runtime_rom.py" --build "$(dirname "$(dirname "$B")")" --runtime "$O/$n" --viamap "$KV_DCAL_VIAMAP" || return 2; fi; ( cd $O/$n && /usr/bin/time -f "%e s %M KB" -o time $B +FRAMES=$I/frames.hex +EXPECT=$I/expect.txt +EPOCH=$EP "${BOOT_ARGS[@]}" "$@" > sim.log 2>&1; echo $? > exit ); }
run nominal &
[ -n "$MF" ] && run mut_frame +MUT_FRAME=$MF &
wait
# TOK-QK-3 10-27: VERDICT from the bench verdict line (kv_verdict.py), never from exit 0; mut_* runs are negative controls.
H=$(cd "$(dirname "$0")" && pwd)
for d in $O/*/; do n=$(basename $d); x=pass; case $n in mut_*) x=fail ;; esac
  v=$(python3 -I $H/kv_verdict.py $d --expect $x)
  echo "$n exit=$(cat $d/exit) $(cat $d/time) VERDICT $v | $(grep -m1 '^KVSLICE_BOOT' $d/sim.log)"; done | tee $O/summary.txt
grep -q -e ' VERDICT FAIL' -e ' VERDICT MUTANT_MISSED' $O/summary.txt && exit 3
exit 0
