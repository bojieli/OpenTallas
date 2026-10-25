#!/bin/bash
# QC-PHYS f57 (from run_rp1.sh): proto starts at CTS from the copied f56c 3_place (no re-synth / re-place).
#   run_rp1.sh KIT proto [MEM_GB=16] [CPUS=8]   sdc_lint -> synth -> face_guard -> place -> CTS(+leaf balance, CTS gate)
#                                               -> GRT(+leaf balance on GRT RC, DRV) -> independent TT/FF GRT measurement
#   run_rp1.sh KIT route [MEM_GB=16] [CPUS=8]   (constraint.sdc / sdc_lint.json already carry vclk latency = I):
#                                               4_cts.sdc vclk latency := I -> GRT again (+hold margin 0..5) -> measure
#                                               -> detailed route -> finish -> abstract -> pin audit -> signoff.py tt,ff
set -uo pipefail
K=$(cd "$1" && pwd); PH=$2; MEM=${3:-16}; CPUS=${4:-8}
IMAGE=${OT_ORFS_IMAGE:-openroad/orfs:asap7lock}
NAME=qcphys-rp1-$(basename "$K")-$PH
TOP=$(sed -n 's/^export DESIGN_NAME = //p' "$K/config.mk")
NICK=$(sed -n 's/^export DESIGN_NICKNAME = //p' "$K/config.mk")
SKIP=$(cat "$K/face_guard_skip.txt")
B=/work/run/results/asap7/$NICK/base
MEAS="for c in TT FF; do OT_VCLK_FF=auto OT_CTAP_CORR=/work/ctap_corr.tcl MC=\$c ODB=$B/5_1_grt.odb SDC=$B/5_1_grt.sdc OUT=/work/meas_${PH}_\$c /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /work/measure.tcl > /work/meas_${PH}_\$c.log 2>&1; grep -h '^RP1_' /work/meas_${PH}_\$c.log; done"
if [ "$PH" = proto ]; then
  STEPS="python3 -I /work/sdc_lint.py /work --liberty \$(ls /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_*RVT_*.lib* 2>/dev/null | grep -v FAKE) > /work/sdc_lint.log 2>&1; rc=\$?; tail -3 /work/sdc_lint.log; \
  if [ \$rc = 0 ]; then \$M do-cts; rc=\$?; fi; \
  if [ \$rc = 0 ]; then \$M do-5_1_grt OT_GRT_HOLD=0; rc=\$?; fi; \
  if [ \$rc = 0 ]; then $MEAS; fi"
elif [ "$PH" = route ]; then
  STEPS="python3 -I /work/sdc_lint.py /work --liberty \$(ls /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_*RVT_*.lib* 2>/dev/null | grep -v FAKE) > /work/sdc_lint.log 2>&1; rc=\$?; tail -3 /work/sdc_lint.log; \
  if [ \$rc = 0 ]; then python3 -I /work/set_vclk.py $B/4_cts.sdc /work/constraint.sdc; rc=\$?; fi; \
  if [ \$rc = 0 ]; then OT_VCLK_FF=auto OT_VCLK_TT=320 \$M do-5_1_grt OT_GRT_HOLD=1 CORNER=BC CORNERS=bc; rc=\$?; fi; \
  if [ \$rc = 0 ]; then $MEAS; fi; \
  if [ \$rc = 0 ]; then bash /work/ff_gate.sh; rc=\$?; fi; \
  if [ \$rc = 0 ]; then \$M do-5_2_route do-5_3_fillcell do-5_route do-5_route.sdc; rc=\$?; fi; \
  if [ \$rc = 0 ]; then \$M do-finish && \$M do-generate_abstract; rc=\$?; fi; \
  O=\$(ls $B/6_final.odb 2>/dev/null | tail -1); \
  if [ -n \"\$O\" ]; then ODB=\$O PINS=/work/pins.json OUT=/work/pin_audit.json openroad -python -exit /work/pin_audit.py; \
    for c in TT FF; do OT_CORNER=\$c DESIGN_NAME=$TOP ODB=\$O SPEF=\${O%.odb}.spef openroad -exit /work/corners.tcl > /work/sta_\$c.log 2>&1; done; fi"
else echo "phase proto|route"; exit 2; fi
echo "image $IMAGE $(docker image inspect --format '{{.Id}}' $IMAGE) host $(hostname) phase $PH start $(date -Is)" >> "$K/image.txt"
docker run --rm --name "$NAME" --cpus="$CPUS" --memory="${MEM}g" --memory-swap="${MEM}g" -v "$K":/work \
  -e HUID=$(id -u) -e HGID=$(id -g) -w /OpenROAD-flow-scripts/flow "$IMAGE" bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; \
  M='make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=$CPUS'; rc=0; \
  $STEPS; chown -R \$HUID:\$HGID /work; exit \$rc" > "$K/run_$PH.log" 2>&1
rc=$?
docker run --rm -v "$K":/work "$IMAGE" chown -R $(id -u):$(id -g) /work >/dev/null 2>&1
echo "end $PH $(date -Is) rc $rc" >> "$K/image.txt"
grep -h '^RP1_' "$K/run_$PH.log" | tail -20
if [ $rc = 0 ] && [ "$PH" = route ]; then
  SIGNOFF_DOCKER=docker python3 -I "$K/signoff.py" run --run-dir "$K/run" --kit "$K" --corners tt,ff \
    --out "$K/signoff" --image "$IMAGE" > "$K/signoff.log" 2>&1
  grep -E '^SIGNOFF|^  - ' "$K/signoff.log" | head -12
fi
exit $rc
