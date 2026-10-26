#!/bin/bash
# PATH-QC 2026-10-26 A0 raw leaf lsl_rawfault_m3 runner (GEOM-REVIEW-10 00:48 PASS-COND option A, goal route to sign-off).
# Continues the reviewed 4_cts in run_ffpg: FF GRT hold repair (the ONLY repair; vclk bound to FF insertion by
# grt_pre.tcl/vclk_corner.tcl) -> detail route -> finish -> abstract -> exact sign-off (signoff.py, TT+FF).
# Usage: run_kit.sh KITDIR [GOAL=route] [MEM_GB=24] [CPUS=8]
set -uo pipefail
K=$(cd "$1" && pwd); GOAL=${2:-route}; MEM=${3:-24}; CPUS=${4:-8}
IMAGE=${OT_ORFS_IMAGE:-openroad/orfs:asap7lock}
NAME=dpkit-$(basename "$K")-$$
B=/work/run_ffpg/results/asap7/lsl_rawfault_m3/base
docker run --rm --name "$NAME" --cpus="$CPUS" --memory="${MEM}g" --memory-swap="${MEM}g" -v "$K":/work \
  -e HUID=$(id -u) -e HGID=$(id -g) -w /OpenROAD-flow-scripts/flow "$IMAGE" bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; \
  M='make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run_ffpg FLOW_VARIANT=base NUM_CORES=$CPUS'; rc=0; \
  if [ ! -f $B/4_cts.sdc.clockonly ]; then cp $B/4_cts.sdc $B/4_cts.sdc.clockonly; fi; cp /work/constraint.sdc $B/4_cts.sdc; \
  HM=\$(sed -n 's/^export OT_HOLD_FF_MARGIN = //p' /work/config.mk | tail -1); \
  if [ $GOAL = route ]; then OT_VCLK_CORNER=ff \$M grt CORNER=BC CORNERS=bc HOLD_SLACK_MARGIN=\$HM; rc=\$?; fi; \
  if [ \$rc = 0 ]; then \$M $GOAL; rc=\$?; fi; \
  if [ \$rc = 0 ] && [ $GOAL = route ]; then \$M do-finish; rc=\$?; fi; \
  if [ \$rc = 0 ] && { [ $GOAL = route ] || [ $GOAL = finish ]; }; then \$M do-generate_abstract; rc=\$?; fi; \
  chown -R \$HUID:\$HGID /work; exit \$rc" > "$K/run_$GOAL.log" 2>&1
rc=$?
docker run --rm -v "$K":/work "$IMAGE" chown -R $(id -u):$(id -g) /work >/dev/null 2>&1
tail -5 "$K/run_$GOAL.log"
if [ $rc = 0 ] && { [ $GOAL = route ] || [ $GOAL = finish ]; }; then
  SO="$K/signoff"; [ ! -e "$SO/signoff.json" ] || SO="$K/signoff_$(date +%Y%m%d_%H%M%S)_$$"
  SIGNOFF_DOCKER=${SIGNOFF_DOCKER:-docker} python3 -I "$K/signoff.py" run --run-dir "$K/run_ffpg" --kit "$K" \
    --out "$SO" --image "$IMAGE" --corners tt,ff > "$SO.log" 2>&1
  grep -E '^SIGNOFF|^  - ' "$SO.log" | head -12
fi
exit $rc
