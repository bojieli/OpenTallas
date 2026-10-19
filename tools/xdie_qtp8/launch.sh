#!/usr/bin/env bash
# TOKEN-XDIE-QTP8 launcher (run locally under nohup): stages this worktree's vehicle sources to the fleet, runs every case
# of tools/xdie_qtp8/cases.py as its own ot-run job (no host pin; memory admission only), copies each case's record/logs
# back (no build objects), then folds them with tools/xdie_qtp8/record.py.  Usage: launch.sh [case ...]
set -u
W=$(cd "$(dirname "$0")/../.." && pwd)
# Q-COLLCAL 10-18: QTP8_RD / QTP8_OUT select a separate fleet stage dir / result dir (defaults = TOKEN-XDIE-QTP8)
RD=${QTP8_RD:-/srv/opentallas-scratch/claude/xdie-qtp8-1018/src}
OUTREL=${QTP8_OUT:-results/rtl/xdie_qtp8_1018}
HOSTS="ot-epyc5 ot-epyc4 ot-pve1 ot-agidock128"
LOG=$W/$OUTREL/ot_run
mkdir -p "$LOG"
OK=()
SSH='ssh -o ControlPath=none -o ConnectTimeout=15 -o ServerAliveInterval=15 -o ServerAliveCountMax=3'
for h in $HOSTS; do   # stage fully or not at all (a partial tree on a host would be picked by --dir): marker written last
  if timeout 300 $SSH "$h" "rm -rf $RD.part && mkdir -p $RD.part" && \
     timeout 600 rsync -a --exclude "/$OUTREL" --exclude '.git' --include '/results/' --include '/results/rtl/' --include '/results/rtl/q_collcal_1018/***' --include '/results/rtl/qcollcal_rl_1018/' --include '/results/rtl/qcollcal_rl_1018/gen_*/***' --include '/results/rtl/mu_qwen_1018/' --include '/results/rtl/mu_qwen_1018/coll/' --include '/results/rtl/mu_qwen_1018/coll/mu_cal.json' --exclude '/results/**' -e "$SSH" "$W/" "$h:$RD.part/" && \
     timeout 120 $SSH "$h" "rm -rf $RD && mv $RD.part $RD && touch $RD/.staged"; then OK+=("$h"); else
     echo "stage to $h failed (skipped)"; timeout 60 $SSH "$h" "rm -rf $RD.part" ; fi
done
HL=$(IFS=,; echo "${OK[*]}"); echo "staged on: $HL"
[ -n "$HL" ] || { echo "no host staged"; exit 1; }
CASES=${*:-$(python3 "$W/tools/xdie_qtp8/cases.py" list)}
pids=()
for c in $CASES; do
  args=$(python3 "$W/tools/xdie_qtp8/cases.py" args "$c")
  ( /home/ubuntu/bin/ot-run --mem 32 --threads 16 --hosts "$HL" --dir "$RD" -- \
      bash -lc "export OT_VERILATOR=\$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator; python3 tools/qwen_coll_tp8_static_links_bench.py --out $OUTREL/$c $args; rc=\$?; rm -rf $OUTREL/$c/obj_*; exit \$rc" \
      > "$LOG/$c.log" 2>&1
    h=$(grep -o 'RAN on [^:]*' "$LOG/$c.log" | tail -1 | awk '{print $3}')
    [ -n "$h" ] && rsync -a -e "$SSH" --exclude 'obj_*' "$h:$RD/$OUTREL/$c/" "$W/$OUTREL/$c/"
  ) &
  pids+=($!)
done
for p in "${pids[@]}"; do wait "$p"; done
QTP8_OUT=$OUTREL python3 "$W/tools/xdie_qtp8/record.py" > "$LOG/record.out" 2>&1; echo "record rc=$?" >> "$LOG/record.out"
echo "LAUNCH DONE $(date -Is)" >> "$LOG/record.out"
