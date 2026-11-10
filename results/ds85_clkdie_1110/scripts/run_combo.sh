#!/bin/bash
# DS85 CLKDIE-S81: clock-only die GRT route (combo.tcl from ds85_combo.py), TT and FF in parallel, read-only kit mounts.
set -uo pipefail
W=/srv/opentallas-scratch2/claude/die-s81-85/clkdie
R=$W/route
image=openroad/orfs:asap7lock
docker image inspect "$image" --format '{{.Id}}' > "$R/route_image.txt"
for c in TT FF; do
  docker run --rm --name ds85-clk-route-$c --memory=128g --cpus=16 \
    -v "$W/ck/kit:/work:ro" -v "$W/clock2:/clock:ro" -v "$R:/out" \
    -e CORNER=$c -e LIBDIR=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM "$image" \
    bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; /usr/bin/time -v openroad -no_init -exit -threads 16 /out/combo.tcl' \
    > "$R/combo_$c.log" 2>&1 &
done
wait
grep -h OT_DONE "$R"/combo_*.log
