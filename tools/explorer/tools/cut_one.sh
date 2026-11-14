#!/bin/bash
# cut one layout pack from an archived signed DB on the archive host (EXPLORER-FABLE-1, COORD GO 2026-11-14)
# usage: cut_one.sh <node id> <kind|path>
W=/srv/opentallas-scratch/claude/explorer-cut-1114
node="$1"; kind="${2%%|*}"; src="${2#*|}"
out=$W/cut/$node; mkdir -p "$out"
[ -f "$out/cut.json" ] && grep -q '"verify": "IDENTICAL"' "$out/cut.json" && { echo "$node DONE already"; exit 0; }
db="$src"
if [ "$kind" = closed_archive ]; then
  mkdir -p "$W/db/$node"; db="$W/db/$node/6_final.odb"
  [ -s "$db" ] || nice -n 15 zstd -q -d -f "$src" -o "$db" || { echo "$node UNZSTD_FAIL"; exit 2; }
elif [ "$kind" != signed-export-1114 ]; then echo "$node SKIP no local archive copy ($src)"; exit 4; fi
size=$(stat -c %s "$db"); mem=$(( size * 16 / 1000000000 + 16 ))   # the tile step (outside the container) peaks well above the extraction
cd $W
ot-heavy --mem $mem -- python3 -I tools/fleet_viz/design_export.py cut --node "$node" --db "$db" --work "$out" --py "$(command -v python3)" --node-bin "$(command -v node)" --db-label "rtx-pro:$src" --no-timing --drop-raw > "$out/cut.log" 2>&1
rc=$?
[ "$kind" = closed_archive ] && rm -rf "$W/db/$node"
echo "$node rc=$rc $(grep -o '"verify": "[A-Z]*"' "$out/cut.json" 2>/dev/null) $(tail -1 "$out/cut.log" | cut -c1-160)"
exit $rc
