#!/bin/bash
# publish every finished, verified pack to the explorer store on epyc8 (only the pack, verify.json and cut.json travel)
W=/srv/opentallas-scratch/claude/explorer-cut-1114; F=/srv/opentallas-scratch2/claude/explorer-fable-1; X=/srv/opentallas-scratch2/claude/explorer-2-work
S="ssh -n -o BatchMode=yes -o ControlPath=none -o ConnectTimeout=10"; n=0
for d in $W/cut/*/; do
  node=$(basename "$d"); [ -f "$d/published" ] && continue
  grep -q '"verify": "IDENTICAL"' "$d/cut.json" 2>/dev/null || continue
  [ -s "$d/$node.lvp" ] || continue
  timeout 60 $S epyc8 "mkdir -p $F/incoming/$node" || continue
  timeout 900 scp -q -o BatchMode=yes -o ControlPath=none "$d/$node.lvp" "$d/verify.json" "$d/cut.json" epyc8:$F/incoming/$node/ || { echo "$node COPY_FAIL"; continue; }
  out=$(timeout 900 $S epyc8 "set -a; . $X/explorer2.env; set +a; cd $F/wt/tools/fleet_viz && nice -n 10 $X/rt/venv/bin/python3 -I design_export.py publish --node $node --pack $F/incoming/$node/$node.lvp --index \$DESIGN_INDEX --store \$LV_STORE 2>&1 | tail -1; rm -rf $F/incoming/$node")
  echo "$node $out" | cut -c1-220
  case "$out" in *published*) date > "$d/published"; n=$((n+1));; esac
done
[ $n -gt 0 ] && timeout 60 $S epyc8 "systemctl --user start --no-block explorer2-refresh.service"
echo "published $n"
