#!/usr/bin/env bash
# TOKEN-XDIE-QTP8 launcher (run locally under nohup): stages this worktree's vehicle sources to the fleet, runs every case
# of tools/xdie_qtp8/cases.py as its own ot-run job (no host pin; memory admission only), copies each case's record/logs
# back (no build objects), then folds them with tools/xdie_qtp8/record.py.  Usage: launch.sh [case ...]
set -u
W=$(cd "$(dirname "$0")/../.." && pwd)
RD=/srv/opentallas-scratch/claude/xdie-qtp8-1018/src
HOSTS="ot-epyc5 ot-epyc4 ot-pve1 ot-agidock128"
LOG=$W/results/rtl/xdie_qtp8_1018/ot_run
mkdir -p "$LOG"
for h in $HOSTS; do
  ssh -o ConnectTimeout=15 "$h" "mkdir -p $RD" && \
  rsync -a --delete --exclude 'results/rtl/xdie_qtp8_1018' --exclude '.git' -e 'ssh -o ConnectTimeout=15' "$W/" "$h:$RD/" \
    || echo "stage to $h failed (skipped)"
done
CASES=${*:-$(python3 "$W/tools/xdie_qtp8/cases.py" list)}
pids=()
for c in $CASES; do
  args=$(python3 "$W/tools/xdie_qtp8/cases.py" args "$c")
  ( /home/ubuntu/bin/ot-run --mem 16 --threads 16 --dir "$RD" -- \
      bash -lc "export OT_VERILATOR=\$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator; python3 tools/qwen_coll_tp8_static_links_bench.py --out results/rtl/xdie_qtp8_1018/$c $args; rc=\$?; rm -rf results/rtl/xdie_qtp8_1018/$c/obj_*; exit \$rc" \
      > "$LOG/$c.log" 2>&1
    h=$(grep -o 'RAN on [^:]*' "$LOG/$c.log" | tail -1 | awk '{print $3}')
    [ -n "$h" ] && rsync -a -e 'ssh -o ConnectTimeout=15' --exclude 'obj_*' "$h:$RD/results/rtl/xdie_qtp8_1018/$c/" "$W/results/rtl/xdie_qtp8_1018/$c/"
  ) &
  pids+=($!)
done
for p in "${pids[@]}"; do wait "$p"; done
python3 "$W/tools/xdie_qtp8/record.py" > "$LOG/record.out" 2>&1; echo "record rc=$?" >> "$LOG/record.out"
echo "LAUNCH DONE $(date -Is)" >> "$LOG/record.out"
