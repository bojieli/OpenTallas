#!/bin/bash
# Prepared only: execute after actual routed signoff says SIGNED.
set -euo pipefail
K=$(realpath "$1"); OUT=$(realpath "$2"); SIGNOFF_JSON=$(realpath "$3"); MASTER=${4:-ot_s81sl_cap_rt}
python3 -I -c 'import json,sys; assert json.load(open(sys.argv[1]))["verdict"]=="SIGNED", "actual SIGNED receipt required"' "$SIGNOFF_JSON"
F=$(find "$K/run/results/asap7" -path '*/base/6_final.odb' -print -quit)
[ -f "$F" ] && [ -f "${F%.odb}.spef" ]
python3 -I -c 'import json,pathlib,sys; d=json.load(open(sys.argv[1])); assert pathlib.Path(d["inputs"]["odb"]).resolve()==pathlib.Path(sys.argv[2]).resolve(), "SIGNED receipt must reference this actual routed ODB"' "$SIGNOFF_JSON" "$F"
REL=${F#"$K"/}
docker run --rm --name codex-caprt-etm1131-$$ --cpus=2 --memory=8g --memory-swap=8g -v "$K":/work:ro -v "$OUT":/out -v "$(dirname "$0")/corners_exact1131.tcl":/export.tcl:ro -e HUID=$(id -u) -e HGID=$(id -g) -e ODB=/work/$REL -e SPEF=/work/${REL%.odb}.spef -e EXPORT_MASTER="$MASTER" -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc '
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
rc=0
for c in TT FF; do OT_CORNER=$c openroad -threads 2 -exit /export.tcl > /out/export_${c}.log 2>&1 || { rc=$?; break; }; done
chown -R "$HUID:$HGID" /out
exit "$rc"
'
