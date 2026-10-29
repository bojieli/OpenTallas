#!/usr/bin/env bash
set -euo pipefail
CORNER=$1
Q=/srv/opentallas-scratch2/claude/die-qc24-1028
K=$Q/trial24
O=$Q/c24_$CORNER
mkdir -p "$O"
CORNER=$CORNER python3 /srv/opentallas-scratch2/claude/die-qc19-1028/mk_clkfirst13.py "$K" "$K/clock" "$O" clk 2w2s > "$O/mk.log" 2>&1
docker run --rm --name qc24-clock24-${CORNER}-$$ --memory=48g --memory-swap=48g --cpus=8 -e CORNER="$CORNER" -e LIBDIR=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM -v "$K":/work:ro -v "$O":/out openroad/orfs:asap7lock bash -lc '
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
set +e
/usr/bin/time -v openroad -no_init -threads 8 -exit /out/clk.tcl > /out/clock.log 2>&1
rc=$?
echo "EXIT $rc" >> /out/clock.log
chown -R '"$(id -u):$(id -g)"' /out
exit "$rc"
'
