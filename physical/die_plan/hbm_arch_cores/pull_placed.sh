#!/bin/bash
# ELEM-HBM: pull small place/route artefacts of every launched kit back from its host into kits_tt/<kit>/ and render
# the placed view (render_core_placed.py) for the placed-stage review.   pull_placed.sh
B=/srv/opentallas-scratch/claude/elem-hbm; H=$(dirname "$0")
grep -o '[a-zA-Z0-9_]* -> [a-z0-9]*:' $B/launch.log | sort -u | while read kit arrow host; do
  host=${host%:}; kd=$B/kits_tt/$kit; [ -d "$kd" ] || continue
  src=$B/runs/$kit
  if [ "$host" = localhost ]; then pre=""; else pre="$host:"; fi
  rsync -a --include='placed.csv' --include='ot_face_flops.txt' --include='face_guard.json' --include='run_*.log' \
    --include='sdc_lint.log' --include='pin_audit.json' --include='views/***' --exclude='*' "$pre$src/" "$kd/" 2>/dev/null </dev/null
  if [ -f "$kd/placed.csv" ] && [ ! -f "$kd/placed.png" -o "$kd/placed.csv" -nt "$kd/placed.png" ]; then
    python3 $H/render_core_placed.py "$kd" "$kd/placed.csv" "$kd/ot_face_flops.txt" "$kd/placed.png" > /dev/null 2>&1 || echo "render fail $kit"
  fi
done
