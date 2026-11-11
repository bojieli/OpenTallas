#!/bin/bash
# CPL-S81-LEAF-3 t35 v2 place + GRT-only probe (DO_NOT_COUNT, no CTS/DRT, no retries). Based on CPL-S81-MISC probe1.sh.
# arm stock = geom_grt on the p4 kit's own 3_place.odb (read-only); arm new = do-floorplan + do-place on the patched
# p4 kit copy (t35_kitpatch.py: bands spread, 2 lane moves, tap cap 1500), then geom_grt. Both M2-M7, adj 0.25, 50 it.
set -uo pipefail
D=/srv/opentallas-scratch2/claude/cpl-s81-leaf-3/t35probe; K=$D/kit; MEM=24; CPUS=8
P4=/srv/opentallas-scratch2/claude/type-safe-5/rs/p4iw/runs/s81/kit-wave/s81/e9eda32d41c/items/ot_s81sl_leaf__t35/attempt_1/gen/ot_s81sl_leaf__t35/run/results/asap7/dp_ot_s81sl_leaf__t35/base
CP="clk $(seq -f 'clk_t%g' 1 37 | tr '\n' ' ')"
N=cpll3-t35-$$
grt() {  # $1 tag, $2 host dir with odb, $3 odb name
  docker run --rm --name "$N-grt-$1" --cpus="$CPUS" --memory="${MEM}g" --memory-swap="${MEM}g" -v "$2":/odb:ro -v "$D":/out -v "$K/geom_grt.tcl":/g.tcl:ro \
    -e OT_GRT_ODB=/odb/$3 -e OT_GRT_MIN=M2 -e OT_GRT_MAX=M7 -e OT_GRT_ADJ=0.25 -e OT_GRT_ITER=50 -e OT_GRT_RPT=/out/grt_$1.rpt -e "OT_GRT_CLOCK_PORTS=$CP" \
    -w /out openroad/orfs:asap7lock bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -exit -threads $CPUS /g.tcl; rc=\$?; chown -R $(id -u):$(id -g) /out; exit \$rc" > "$D/grt_$1.log" 2>&1
  echo "GRT $1 rc=$? $(date)" >> "$D/probe.status"
}
echo "START $(date) host $(hostname)" >> "$D/probe.status"
grt stock "$P4" 3_place.odb &
docker run --rm --name "$N" --cpus="$CPUS" --memory="${MEM}g" --memory-swap="${MEM}g" -v "$K":/work \
  -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; \
  M='make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=$CPUS'; \
  \$M do-floorplan && \$M do-place; rc=\$?; chown -R $(id -u):$(id -g) /work; exit \$rc" > "$D/probe_place.log" 2>&1
rc=$?; echo "PLACE new rc=$rc $(date)" >> "$D/probe.status"
[ $rc = 0 ] && grt new "$K/run/results/asap7/dp_ot_s81sl_leaf__t35/base" 3_place.odb
wait
for t in stock new; do echo "== $t" >> "$D/probe.status"; grep -A14 "Final congestion report" "$D/grt_$t.log" >> "$D/probe.status" 2>/dev/null; done
echo "END $(date)" >> "$D/probe.status"
