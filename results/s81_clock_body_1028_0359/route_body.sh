#!/bin/bash
set -euo pipefail
r=/srv/opentallas-scratch2/claude/codex-s81-owner-0359/clock_body
b=/srv/opentallas-scratch2/claude/die-s81-7/kit_G
image=openroad/orfs:asap7lock
docker image inspect "$image" --format '{{.Id}}' > "$r/route_image.txt"
for c in TT FF; do
 docker run --rm --memory=64g --cpus=8 -v "$b:/work:ro" -v "$r/route_$c:/out" -e CORNER="$c" -e LIBDIR=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM "$image" bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -no_init -exit -threads 8 /out/combo.tcl' > "$r/route_$c/combo_$c.log" 2>&1
 done
