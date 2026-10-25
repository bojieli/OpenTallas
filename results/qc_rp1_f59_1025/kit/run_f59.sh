#!/bin/bash
# PATH-QC-RP1-F59 runner = run_f58.sh flow steps (CTS onward unchanged) + a full front end:
#   run_f59.sh KIT place [MEM] [CPUS]  run_kit.sh place (sdc_lint -> synth MIF=1 -> face_guard -> floorplan -> place with
#                                      pre_gpl.tcl anchors) -> keep_check.py -> F6 dump on 3_place (reviewer dumpif form)
#   run_f59.sh KIT proto               sdc_lint -> CTS(+taps, gate) -> GRT(no hold) -> TT/FF GRT measurement
#   run_f59.sh KIT gate                proto if missing -> set_vclk -> GRT(+FF hold repair, OT_VCLK_FF=auto) -> measure ->
#                                      ff_gate.sh (FF hold >= 0 at 0 EP + related-pair TT/FF <= 80) -> F6 on 5_1_grt; STOP
#   run_f59.sh KIT route|finish        gate first unless gate_pass.txt is newer than 5_1_grt.odb, then DRT -> finish ->
#                                      abstract -> pin audit -> routed tap report -> signoff.py tt,ff --ff-vclk auto
# (autopilot calls: bash run_f59.sh KIT GOAL MEM THREADS; log = KIT/run_GOAL.log)
set -uo pipefail
K=$(cd "$1" && pwd); PH=$2; MEM=${3:-16}; CPUS=${4:-8}
IMAGE=${OT_ORFS_IMAGE:-openroad/orfs:asap7lock}
NAME=pathqc-rp1-$(basename "$K")-$PH-$$
TOP=$(sed -n 's/^export DESIGN_NAME = //p' "$K/config.mk")
NICK=$(sed -n 's/^export DESIGN_NICKNAME = //p' "$K/config.mk")
B=/work/run/results/asap7/$NICK/base; HB=$K/run/results/asap7/$NICK/base
LINT="python3 -I /work/sdc_lint.py /work --liberty \$(ls /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_*RVT_*.lib* 2>/dev/null | grep -v FAKE) > /work/sdc_lint.log 2>&1; rc=\$?; tail -3 /work/sdc_lint.log"
MEAS="for c in TT FF; do OT_VCLK_FF=auto OT_CTAP_CORR=/work/ctap_corr.tcl MC=\$c ODB=$B/5_1_grt.odb SDC=$B/5_1_grt.sdc OUT=/work/meas_${PH}_\$c /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /work/measure.tcl > /work/meas_${PH}_\$c.log 2>&1; grep -h '^RP1_' /work/meas_${PH}_\$c.log; done"
if [ "$PH" = place ]; then
  "$K/run_kit.sh" "$K" place "$MEM" "$CPUS"; rc=$?
  echo "f59 place rc $rc $(date -Is)" >> "$K/image.txt"; [ $rc = 0 ] || exit $rc
  python3 -I "$K/keep_check.py" "$K" > "$K/keep_check.txt" 2>&1; rc=$?; cat "$K/keep_check.txt"
  [ $rc = 0 ] || { echo "f59 KEEP_CHECK FAIL" >> "$K/image.txt"; exit 7; }
  bash "$K/f6_dump.sh" "$K" 3_place > "$K/f6_place.log" 2>&1; grep -h '^F6' "$K/f6_place.log"
  exit 0
fi
if [ "$PH" != proto ] && [ ! -f "$HB/5_1_grt.odb" -o ! -f "$K/meas_proto_FF.log" ]; then
  bash "$0" "$K" proto "$MEM" "$CPUS" || { echo "proto phase failed"; exit 1; }
fi
if { [ "$PH" = route ] || [ "$PH" = finish ]; } && ! { [ -f "$K/gate_pass.txt" ] && [ "$K/gate_pass.txt" -nt "$HB/5_1_grt.odb" ]; }; then
  bash "$0" "$K" gate "$MEM" "$CPUS" || { echo "gate phase failed (no detailed route)"; exit 3; }
fi
GATE="\$M do-5_1_grt OT_GRT_HOLD=1 CORNER=BC CORNERS=bc OT_VCLK_FF=auto OT_VCLK_TT=320"
if [ "$PH" = proto ]; then
  STEPS="$LINT; if [ \$rc = 0 ]; then \$M do-cts; rc=\$?; fi; \
  if [ \$rc = 0 ]; then \$M do-5_1_grt OT_GRT_HOLD=0; rc=\$?; fi; \
  if [ \$rc = 0 ]; then $MEAS; fi"
elif [ "$PH" = gate ]; then
  rm -f "$K/gate_pass.txt"
  STEPS="$LINT; if [ \$rc = 0 ]; then python3 -I /work/set_vclk.py $B/4_cts.sdc /work/constraint.sdc; rc=\$?; fi; \
  if [ \$rc = 0 ]; then OT_VCLK_FF=auto OT_VCLK_TT=320 \$M do-5_1_grt OT_GRT_HOLD=1 CORNER=BC CORNERS=bc; rc=\$?; fi; \
  if [ \$rc = 0 ]; then $MEAS; fi; \
  if [ \$rc = 0 ]; then bash /work/ff_gate.sh /work/meas_gate; rc=\$?; fi"
elif [ "$PH" = route ] || [ "$PH" = finish ]; then
  STEPS="rc=0; \$M do-5_2_route do-5_3_fillcell do-5_route do-5_route.sdc; rc=\$?; \
  if [ \$rc = 0 ]; then \$M do-finish && \$M do-generate_abstract; rc=\$?; fi; \
  O=\$(ls $B/6_final.odb 2>/dev/null | tail -1); \
  if [ -n \"\$O\" ]; then ODB=\$O PINS=/work/pins.json OUT=/work/pin_audit.json openroad -python -exit /work/pin_audit.py; \
    for c in TT FF; do OT_CORNER=\$c DESIGN_NAME=$TOP ODB=\$O SPEF=\${O%.odb}.spef openroad -exit /work/corners.tcl > /work/sta_\$c.log 2>&1; \
      MC=\$c ODB=\$O SPEF=\${O%.odb}.spef SDC=\$(ls $B/6_final.sdc $B/5_route.sdc 2>/dev/null | head -1) /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /work/macro_rcx_graph.tcl > /work/macro_rcx_\$c.log 2>&1; \
      grep -h \"OT_CTAP_M itfinal\" /work/macro_rcx_\$c.log | sed \"s/^/RP1_RCX \$c /\"; done; fi"
else echo "phase place|proto|gate|route"; exit 2; fi
echo "image $IMAGE $(docker image inspect --format '{{.Id}}' $IMAGE) host $(hostname) phase $PH start $(date -Is)" >> "$K/image.txt"
docker run --rm --name "$NAME" --cpus="$CPUS" --memory="${MEM}g" --memory-swap="${MEM}g" -v "$K":/work \
  -e HUID=$(id -u) -e HGID=$(id -g) -w /OpenROAD-flow-scripts/flow "$IMAGE" bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; \
  M='make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=$CPUS'; rc=0; \
  $STEPS; chown -R \$HUID:\$HGID /work; exit \$rc" > "$K/run_$PH.log" 2>&1
rc=$?
docker run --rm -v "$K":/work "$IMAGE" chown -R $(id -u):$(id -g) /work >/dev/null 2>&1
echo "end $PH $(date -Is) rc $rc" >> "$K/image.txt"
grep -h '^RP1_\|OT_CTAP_M itfinal' "$K/run_$PH.log" | tail -30
if [ "$PH" = gate ]; then
  bash "$K/f6_dump.sh" "$K" 5_1_grt > "$K/f6_grt.log" 2>&1; grep -h '^F6' "$K/f6_grt.log"
  [ $rc = 0 ] && grep -h '^RP1_GATE' "$K/run_gate.log" > "$K/gate_pass.txt"
fi
if [ $rc = 0 ] && { [ "$PH" = route ] || [ "$PH" = finish ]; }; then
  SIGNOFF_DOCKER=docker python3 -I "$K/signoff.py" run --run-dir "$K/run" --kit "$K" --corners tt,ff --ff-vclk auto \
    --out "$K/signoff" --image "$IMAGE" > "$K/signoff.log" 2>&1; rc=$?
  grep -E '^SIGNOFF|^  - ' "$K/signoff.log" | head -12
fi
exit $rc
