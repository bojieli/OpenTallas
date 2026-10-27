#!/bin/bash
# HBM-EP-REPACK: floorplan (re-packed SRAMs) -> place -> [optional CTS] -> diagnostic GRT probe.  STAGE=place|cts|grt
# HBM-CORES-R6 10-27 (false success fix): the exit code and the PROBE verdict line are the GRT probe's, never only the
# place/CTS step's.  PASS needs: inner openroad rc 0 + OT_PROBE_GRT_DONE + a GRT-0096 final report + total overflow 0
# at ITERS >= 50 (GEOM-19).  Otherwise the script exits non-zero with PROBE_VERDICT FAIL|ERROR.
set -uo pipefail
K=$(cd "$(dirname "$0")" && pwd); STAGE=${STAGE:-place}; ITERS=${ITERS:-50}; exec >> "$K/probe_$STAGE.log" 2>&1
echo "PROBE start $STAGE iters $ITERS $(date -Is)"
docker run --rm --name eprepack-$STAGE-$$ --cpus=16 --memory=24g --memory-swap=24g -v "$K":/work -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; \
 M=\"make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=16\"; R=\$(ls -d /work/run/results/asap7/*/base 2>/dev/null | head -1); rc=0; \
 if [ $STAGE = place ]; then \$M synth && \$M do-floorplan do-place; rc=\$?; echo PROBE_PLACE rc=\$rc; R=\$(ls -d /work/run/results/asap7/*/base | head -1); O=\$R/3_place.odb; fi; \
 if [ $STAGE = grt ]; then O=\$R/${SRC:-3_place}.odb; fi; \
 if [ $STAGE = cts ]; then \$M do-cts; rc=\$?; echo PROBE_CTS rc=\$rc; O=\$R/4_cts.odb; grep -h OT_MSCTS /work/run/logs/asap7/*/base/4_1_cts.log | tail -5; fi; \
 if [ \$rc = 0 ]; then mkdir -p /work/probe_$STAGE; ODB=\$O OUT=/work/probe_$STAGE ITERS=$ITERS PLATFORM_DIR=/OpenROAD-flow-scripts/flow/platforms/asap7 openroad -exit /work/grt_probe.tcl > /work/probe_$STAGE/grt.log 2>&1; rc=\$?; echo PROBE_GRT rc=\$rc; \
   grep -A10 GRT-0096 /work/probe_$STAGE/grt.log; echo DRT0419 \$(grep -c DRT-0419 /work/probe_$STAGE/grt.log) DRT0421 \$(grep -c DRT-0421 /work/probe_$STAGE/grt.log); fi; \
 chown -R $(id -u):$(id -g) /work; exit \$rc"
rc=$?
G="$K/probe_$STAGE/grt.log"; v=ERROR; why="docker/step rc $rc"; ovf=NA
if [ $rc = 0 ]; then
  if [ ! -s "$G" ] || ! grep -q '^OT_PROBE_GRT_DONE' "$G" || ! grep -q 'GRT-0096' "$G"; then
    why="GRT probe did not complete (no OT_PROBE_GRT_DONE / GRT-0096 in $G)"; rc=5
  else
    ovf=$(awk '/GRT-0096/{f=1} f&&/^Total/{print $NF; exit}' "$G")
    if [ -z "$ovf" ]; then why="no Total line in the GRT-0096 report"; rc=5
    elif [ "$ovf" = 0 ] && [ "$ITERS" -ge 50 ]; then v=PASS; why="overflow 0 at $ITERS it"
    else v=FAIL; why="total overflow $ovf at $ITERS it (PASS = 0 at >= 50)"; rc=6; fi
  fi
fi
echo "PROBE_VERDICT $v stage $STAGE overflow $ovf :: $why"
echo "PROBE end $STAGE rc=$rc $(date -Is)"; exit $rc
