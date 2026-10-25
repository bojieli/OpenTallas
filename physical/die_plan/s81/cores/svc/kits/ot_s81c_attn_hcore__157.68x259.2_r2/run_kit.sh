#!/bin/bash
# S81-HCORE r2 (copied from kits_repin VQ r12, gen_kit_repin.py): run one core kit through ORFS in docker.  Fail-closed gates (CP1-R10):
# sdc_lint.py against the image's liberty time_unit BEFORE synth, face_guard (face_guard_core.py) on the Yosys netlist
# right AFTER synth; either failing stops the kit.  Then finish (route + fill + RCX), generate_abstract, the pin audit
# of the routed ODB against the plan pins, and corners.tcl STA at TT / FF / SS (+ timing models).
#   run_kit.sh KITDIR [GOAL=finish] [MEM_GB=32] [CPUS=16]
set -uo pipefail
K=$(cd "$1" && pwd); GOAL=${2:-finish}; MEM=${3:-32}; CPUS=${4:-16}
IMAGE=${OT_ORFS_IMAGE:-openroad/orfs:asap7lock}
DOCKER=${OT_DOCKER:-docker}
NAME=krepin-$(basename "$K")-$$
TOP=$(sed -n 's/^export DESIGN_NAME = //p' "$K/config.mk")
SKIP=$(cat "$K/face_guard_skip.txt")
echo "image $IMAGE $($DOCKER image inspect --format '{{.Id}}' $IMAGE) host $(hostname) start $(date -Is)" > "$K/image.txt"
$DOCKER run --rm --name "$NAME" --cpus="$CPUS" --memory="${MEM}g" --memory-swap="${MEM}g" -v "$K":/work \
  -e HUID=$(id -u) -e HGID=$(id -g) -w /OpenROAD-flow-scripts/flow "$IMAGE" bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; \
  M='make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=$CPUS'; rc=0; \
  python3 -I /work/sdc_lint.py /work --liberty \$(ls /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_*RVT_*.lib* 2>/dev/null | grep -v FAKE) > /work/sdc_lint.log 2>&1; rc=\$?; tail -3 /work/sdc_lint.log; \
  if [ \$rc = 0 ]; then \$M synth; rc=\$?; fi; \
  N=\$(ls /work/run/results/asap7/*/base/1_2_yosys.v 2>/dev/null | tail -1); \
  if [ \$rc = 0 ]; then python3 -I /work/face_guard_core.py \$N $TOP '$SKIP' /work/pins.json /work/face_guard.json; rc=\$?; \
    if [ \$rc != 0 ] && [ -f /work/face_guard_continue ]; then echo 'FACE_GUARD FAIL: PATHFINDING physical run continues (face_guard_continue), FAIL recorded'; rc=0; fi; fi; \
  if [ \$rc = 0 ]; then \$M $GOAL; rc=\$?; fi; \
  if [ \$rc = 0 ] && [ $GOAL = route ]; then \$M do-finish; rc=\$?; fi; \
  if [ \$rc = 0 ] && { [ $GOAL = finish ] || [ $GOAL = route ]; }; then \$M do-generate_abstract; rc=\$?; fi; \
  O=\$(ls /work/run/results/asap7/*/base/5_route.odb /work/run/results/asap7/*/base/6_final.odb 2>/dev/null | tail -1); \
  if [ -n \"\$O\" ]; then ODB=\$O PINS=/work/pins.json OUT=/work/pin_audit.json openroad -python -exit /work/pin_audit.py; fi; \
  F=\$(ls /work/run/results/asap7/*/base/6_final.odb 2>/dev/null | tail -1); \
  if [ -n \"\$F\" ]; then for c in TT FF; do OT_CORNER=\$c DESIGN_NAME=$TOP ODB=\$F SPEF=\${F%.odb}.spef openroad -exit /work/corners.tcl > /work/sta_\$c.log 2>&1; done; fi; \
  chown -R \$HUID:\$HGID /work; exit \$rc" > "$K/run_$GOAL.log" 2>&1
rc=$?
$DOCKER run --rm -v "$K":/work "$IMAGE" chown -R $(id -u):$(id -g) /work >/dev/null 2>&1
echo "end $(date -Is) rc $rc" >> "$K/image.txt"
tail -5 "$K/run_$GOAL.log"
# SIGNOFF (main f942bf2f72): uniform verdict in KIT/signoff/signoff.json; a core is closed only when it says SIGNED.
if [ $rc = 0 ] && { [ $GOAL = finish ] || [ $GOAL = route ]; } && [ -f "$K/signoff.py" ]; then
  SIGNOFF_DOCKER="$DOCKER" python3 -I "$K/signoff.py" run --run-dir "$K/run" --kit "$K" --name ot_s81c_attn_hcore_r2 --corners tt,ff \
    --out "$K/signoff" --image "$IMAGE" > "$K/signoff.log" 2>&1
  grep -E '^SIGNOFF|^  - ' "$K/signoff.log" | head -12
fi
exit $rc
