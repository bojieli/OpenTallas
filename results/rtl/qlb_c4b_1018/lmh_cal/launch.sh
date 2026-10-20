#!/usr/bin/env bash
# QLB-C4b/2 launcher (local, no sims here): stage this worktree to the fleet, run run.sh under ot-run (memory admission,
# no host pin), copy the logs back (no build objects).   launch.sh [TAG]
set -u
W=$(cd "$(dirname "$0")/../../../.." && pwd)
TAG=${1:-r1}
RD=/srv/opentallas-scratch/claude/qlb-c4b-lmh-1018/src
OUTREL=results/rtl/qlb_c4b_1018/lmh_cal/$TAG
SSH='ssh -o ControlPath=none -o ConnectTimeout=15 -o ServerAliveInterval=15 -o ServerAliveCountMax=3'
OK=()
for h in ot-epyc5 ot-pve1; do
  if timeout 300 $SSH "$h" "rm -rf $RD.part && mkdir -p $RD.part" && \
     timeout 600 rsync -a --exclude '.git' --exclude "/results/rtl/qlb_c4b_1018/lmh_cal/r*/" -e "$SSH" "$W/" "$h:$RD.part/" && \
     timeout 120 $SSH "$h" "rm -rf $RD && mv $RD.part $RD && touch $RD/.staged"; then OK+=("$h"); else
     echo "stage to $h failed"; fi
done
HL=$(IFS=,; echo "${OK[*]}"); echo "staged on: $HL"; [ -n "$HL" ] || exit 1
mkdir -p "$W/$OUTREL"
/home/ubuntu/bin/ot-run --mem 48 --threads 24 --hosts "$HL" --dir "$RD" -- \
  bash -lc "bash results/rtl/qlb_c4b_1018/lmh_cal/run.sh $OUTREL" > "$W/$OUTREL/ot_run.log" 2>&1
h=$(grep -o 'RAN on [^:]*' "$W/$OUTREL/ot_run.log" | tail -1 | awk '{print $3}')
[ -n "$h" ] && rsync -a -e "$SSH" --exclude 'obj_*' "$h:$RD/$OUTREL/" "$W/$OUTREL/"
echo "LAUNCH DONE $(date -Is) host=$h" >> "$W/$OUTREL/ot_run.log"
