#!/bin/bash
set -eu
W=/srv/opentallas-scratch2/claude/wt/codex-qc-su-trials
B=/srv/opentallas-scratch2/claude/codex-qc-su-trials
cd "$W"
python3 - <<'PY' > "$B/views_selected.tsv"
import json
v=json.load(open('/srv/opentallas-scratch2/claude/codex-qc-su-trials/views.json'))
for e in v['view_list']:
 if e['module'] in ['qfd_qc_su_lane_w_l'+str(i) for i in range(3,8)]:print(e['module'],e['view'],sep='\t')
PY
failed=0
while IFS=$'\t' read -r module view; do
  if [ -f "$B/jobs.tsv" ] && awk -v m="$module" '$1==m {found=1} END {exit !found}' "$B/jobs.tsv"; then echo "$module ALREADY_QUEUED"; continue; fi
  out="$B/$module"
  mkdir -p "$out"
  python3 physical/die_plan/qwen_compute/cores/qc_core_wave.py gen --views "$B/views.json" --view "$view" --out "$out" --plan physical/die_plan/qwen_compute/plan_of_record/plan_qc52.json > "$out/gen.log" 2>&1 || { echo "$module GEN_FAIL"; failed=1; continue; }
  kit=$(find "$out" -mindepth 2 -maxdepth 2 -name freeze.json -printf '%h\n' | head -n 1)
  test -n "$kit" || { echo "$module NO_KIT"; failed=1; continue; }
  nohup "$HOME/.local/bin/ot-run" --mem 64 --threads 16 --hosts localhost --dir "$kit" -- bash "$kit/run_kit.sh" "$kit" cts 64 16 > "$out/cts.otrun.log" 2>&1 < /dev/null &
  pid=$!
  echo "$module $pid $kit" | tee -a "$B/jobs.tsv"
done < "$B/views_selected.tsv"
exit "$failed"
