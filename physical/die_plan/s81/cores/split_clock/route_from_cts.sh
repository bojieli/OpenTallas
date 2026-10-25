#!/bin/bash
# route_from_cts.sh KITDIR [GOAL] [MEM_GB=32] [CPUS=16]: continue a cts_only.sh kit (4_cts present) through GRT (BC, as run_kit.sh),
# detail route, finish, abstract, pin audit, TT/FF corner STA and the repo sign-off (KIT/signoff/signoff.json).
# Launch only after a GEOM PASS for the kit (owner rule 10-25).
set -uo pipefail
K=$(cd "$1" && pwd); shift
# autopilot calls RUNNER KIT GOAL MEM THREADS: drop a non-numeric goal
case "${1:-}" in ""|*[!0-9]*) [ $# -gt 0 ] && shift;; esac
MEM=${1:-32}; CPUS=${2:-16}
IMAGE=${OT_ORFS_IMAGE:-openroad/orfs:asap7lock}
TOP=$(sed -n 's/^export DESIGN_NAME = //p' "$K/config.mk")
docker run --rm --name s81split-route-$(basename $K) --cpus="$CPUS" --memory="${MEM}g" --memory-swap="${MEM}g" -v "$K":/work \
  -w /OpenROAD-flow-scripts/flow "$IMAGE" bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; \
  M='make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=$CPUS'; \
  \$M do-5_1_grt CORNER=BC CORNERS=bc HOLD_SLACK_MARGIN=0 && \$M do-5_2_route do-5_3_fillcell do-5_route do-5_route.sdc && \$M do-finish && \$M do-generate_abstract; rc=\$?; \
  O=\$(ls /work/run/results/asap7/*/base/6_final.odb 2>/dev/null | tail -1); \
  if [ -n \"\$O\" ]; then ODB=\$O PINS=/work/pins.json OUT=/work/pin_audit.json openroad -python -exit /work/pin_audit.py; \
    for c in TT FF; do OT_CORNER=\$c DESIGN_NAME=$TOP ODB=\$O SPEF=\${O%.odb}.spef openroad -exit /work/corners.tcl > /work/sta_\$c.log 2>&1; done; fi; \
  chown -R $(id -u):$(id -g) /work; exit \$rc" > "$K/run_route.log" 2>&1
rc=$?; tail -5 "$K/run_route.log"
if [ $rc = 0 ] && [ -f "$K/signoff.py" ]; then
  python3 -I "$K/signoff.py" run --run-dir "$K/run" --kit "$K" --corners tt,ff --out "$K/signoff" --image "$IMAGE" > "$K/signoff.log" 2>&1
  grep -E '^SIGNOFF|^  - ' "$K/signoff.log" | head -12
fi
exit $rc
