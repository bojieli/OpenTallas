#!/usr/bin/env bash
set -euo pipefail
CORNER=$1
Q=/srv/opentallas-scratch2/claude/die-qc8-1028
K=$Q/trial6
O=$Q/c6_$CORNER
mkdir -p "$O"
CORNER=$CORNER python3 "$Q/mk_clkfirst.py" "$K" "$K/clock" "$O" clk 2w2s > "$O/mk.log" 2>&1
docker run --rm --name qc8-clock6-${CORNER}-$$ --memory=48g --memory-swap=48g --cpus=8 -e CORNER="$CORNER" -e LIBDIR=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM -v "$K":/work:ro -v "$O":/out openroad/orfs:asap7lock bash -lc '
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
set +e
/usr/bin/time -v openroad -no_init -threads 8 -exit /out/clk.tcl > /out/clock.log 2>&1
rc=$?
echo "EXIT $rc" >> /out/clock.log
chown -R '"$(id -u):$(id -g)"' /out
exit "$rc"
'
