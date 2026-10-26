#!/bin/bash
# TOK-DS dskr driver (runs nohup on the ot-run client host, epyc1): waits for the 4 cut binaries built by
# tools/s81_dv/run_dv_slice.sh (intel2 cut_7 + cut_3S_ctl, intel1 cut_0S, epyc2 cut_0N), then via ot-run on intel2:
# run_dskr.sh entry (native HOST entry proof on cut_3S_ctl) and run_dskr.sh cuts <each cut> (base / input-corrupt / expect-shift).
# Binaries built elsewhere are copied (obj/sim only) to intel2 first. Usage: drive_dskr.sh <W> (same path on every host)
set -u
W=$1; S=$W/wt/results/token_pass/tokds_dskr_1025/run_dskr.sh; OTR=$HOME/.local/bin/ot-run
SSH="ssh -o ControlPath=none -o ConnectTimeout=20"
declare -A H=([cut_7]=intel2 [cut_3S_ctl]=intel2 [cut_0S]=intel1 [cut_0N]=epyc2)
state() {  # host cut -> ok | fail | wait
  $SSH $1 "f=$W/builds/out_$2; if [ -x \$f/obj/sim ]; then echo ok; elif grep -q 'rc [1-9]' \$f/status 2>/dev/null; then echo fail; else echo wait; fi" 2>/dev/null || echo wait
}
waitfor() { local c=$1 s; while :; do s=$(state ${H[$c]} $c); [ "$s" != wait ] && { echo "$(date) $c $s"; [ $s = ok ]; return; }; sleep 120; done; }
if waitfor cut_3S_ctl; then
  $SSH intel2 "until [ -f $W/builds/out_cut_3S_ctl/run.time ]; do sleep 30; done"   # idle 2000-cycle trace run finished
  $OTR --mem 48 --threads 8 --hosts intel2 --dir $W -- bash $S $W entry
fi
for c in cut_7 cut_0S cut_0N; do
  waitfor $c || continue
  if [ ${H[$c]} != intel2 ]; then
    $SSH intel2 "mkdir -p $W/builds/out_$c/obj" && $SSH ${H[$c]} "cat $W/builds/out_$c/obj/sim" | $SSH intel2 "cat > $W/builds/out_$c/obj/sim && chmod +x $W/builds/out_$c/obj/sim"
  fi
  $OTR --mem 32 --threads 4 --hosts intel2 --dir $W -- bash $S $W cuts $c
done
echo "$(date) DRIVE_DONE"
