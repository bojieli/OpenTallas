#!/bin/bash
# TOKj-KV 10-23: run the KV die-slice vehicle (built by build.sh) on one boot image: nominal + the frame mutant.
#   run.sh OBJDIR IMGDIR OUT [MUT_FRAME]     IMGDIR holds frames.hex expect.txt epoch.txt (bench/boot_frames.py)
set -u
B=$(readlink -f $1)/obj/Vtb_kvslice; I=$(readlink -f $2); O=$(mkdir -p $3 && readlink -f $3); MF=${4:-}
EP=$(cat $I/epoch.txt)
run() { local n=$1; shift; mkdir -p $O/$n; ( cd $O/$n && /usr/bin/time -f "%e s %M KB" -o time $B +FRAMES=$I/frames.hex +EXPECT=$I/expect.txt +EPOCH=$EP "$@" > sim.log 2>&1; echo $? > exit ); }
run nominal &
[ -n "$MF" ] && run mut_frame +MUT_FRAME=$MF &
wait
for d in $O/*/; do echo "$(basename $d) exit=$(cat $d/exit) $(cat $d/time) $(grep -m1 '^KVSLICE_BOOT' $d/sim.log)"; done | tee $O/summary.txt
