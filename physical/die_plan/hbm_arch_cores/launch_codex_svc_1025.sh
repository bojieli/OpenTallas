#!/bin/bash
set -euo pipefail
B=/srv/opentallas-scratch2/claude/codex-hbm-cores-1025
mkdir -p "$B/svc_kits" "$B/launchlogs"
for src in /srv/opentallas-scratch2/claude/hbm-face/kits_all/ot_hbm_svc_pc_ctrl_leaf_cfg_h9b_*; do
 for variant in base pd42; do
  n="$(basename "$src")_shell_$variant"
  k="$B/svc_kits/$n"
  [ ! -e "$k" ] || continue
  mkdir -p "$k"
  cp -a "$src/." "$k/"
  if [ "$variant" = pd42 ]; then echo 'export PLACE_DENSITY = 0.42' >> "$k/config.mk"; fi
  h=$(~/.local/bin/ot-run --hosts epyc2,intel1,intel2 --mem 16 --threads 8 --pick | tail -1)
  rd="$B/runs/$n"
  ssh "$h" "mkdir -p '$rd'"
  rsync -a "$k/" "$h:$rd/"
  nohup ~/.local/bin/ot-run --hosts "$h" --mem 16 --threads 8 --dir "$rd" -- bash "$rd/run_kit_hbm.sh" "$rd" cts 16 8 > "$B/launchlogs/$n.log" 2>&1 < /dev/null &
  pid=$!
  echo "$(date '+%F %T') $n $h:$rd PID=$pid" >> "$B/svc_jobs.txt"
 done
done
