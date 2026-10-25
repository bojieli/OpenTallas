#!/bin/bash
# ELEM-HBM (gen_core_kit_hbm.py): run one HBM B2r2 core kit through ORFS in docker:
#   sdc_lint (CP1-R10, fail-closed, vs the image liberty) -> synth -> face_guard (verdict recorded, flow continues for
#   timing evidence) -> GOAL (finish) -> generate_abstract -> pin audit -> corners_hbm.tcl at SS / FF / TT
#   (STA, face-flop CK spread, ETM).  Outputs chowned back to the caller.
#   run_kit_hbm.sh KITDIR [GOAL=finish] [MEM_GB=32] [CPUS=16]     (heavy: call through ot-run --mem MEM_GB)
#   GOAL=post: no flow steps; pin audit + corners + signoff on the run's existing routed ODB (HBM-ELEM 10-24: the
#   corners step used to read 'make print-X' as 'X = ...' but ORFS prints 'X: ...' -> empty libs -> STA-0453 -> rc+100
#   -> signoff skipped on every finished kit).
set -uo pipefail
# HBM-CORES3 10-25 (COORD KIT-CENSUS): sdc_lint / SELRANGE / port-bind / face_guard FAIL = STOP before floorplan
# (marker /work/FAIL_PREFLOOR, rc 3); post-CTS FF hold gate (hold_gate.tcl: WNS < -100 ps or > 2000 endpoints = STOP,
# marker /work/FAIL_POSTCTS, rc 4: a structural plan/RTL issue, not repaired).
K=$(cd "$1" && pwd -P); GOAL=${2:-finish}; MEM=${3:-32}; CPUS=${4:-16}
IMAGE=${OT_ORFS_IMAGE:-openroad/orfs:asap7lock}
DK=docker; docker ps >/dev/null 2>&1 || DK="sudo docker"
NAME=hbmcore-$(basename "$K" | tr -c 'A-Za-z0-9_.-' _ | cut -c1-60)-$$
$DK run --rm --name "$NAME" --cpus="$CPUS" --memory="${MEM}g" --memory-swap="${MEM}g" -v "$K":/work \
  -e HUID=$(id -u) -e HGID=$(id -g) -w /OpenROAD-flow-scripts/flow "$IMAGE" bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; \
  M='make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=$CPUS'; \
  rc=0; if [ $GOAL != post ]; then rm -f /work/FAIL_PREFLOOR /work/FAIL_POSTCTS; \
  python3 -I /work/sdc_lint.py /work --liberty \$(ls /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_*RVT_*.lib* 2>/dev/null | grep -v FAKE) > /work/sdc_lint.log 2>&1; rc=\$?; tail -2 /work/sdc_lint.log; \
  if [ \$rc != 0 ]; then echo 'FAIL_PREFLOOR sdc_lint' | tee -a /work/FAIL_PREFLOOR; fi; \
  SP=; if [ \$rc = 0 ] && [ -f /work/selrange_gate.py ]; then ( timeout 7200 python3 -I /work/selrange_gate.py /work --out /work/selrange.json > /work/selrange.log 2>&1; echo \$? > /work/selrange.rc ) & SP=\$!; fi; \
  if [ \$rc = 0 ]; then \$M synth; rc=\$?; fi; \
  N=\$(ls /work/run/results/asap7/*/base/1_synth.v /work/run/results/asap7/*/base/1_2_yosys.v 2>/dev/null | head -1); \
  if [ \$rc = 0 ] && [ -n \"\$N\" ]; then python3 -I /work/face_guard_core.py \$N /work > /work/face_guard.log 2>&1; fg=\$?; echo \"face_guard rc \$fg\"; \
    if [ \$fg != 0 ]; then echo 'FAIL_PREFLOOR face_guard' | tee -a /work/FAIL_PREFLOOR; rc=3; fi; \
    python3 -I /work/port_bind_core.py \$N /work > /work/port_bind.log 2>&1; pb=\$?; cat /work/port_bind.log; \
    if [ \$pb != 0 ]; then echo 'FAIL_PREFLOOR port_bind' | tee -a /work/FAIL_PREFLOOR; rc=3; fi; fi; \
  if [ -n \"\$SP\" ]; then wait \$SP; sr=\$(cat /work/selrange.rc 2>/dev/null); echo \"selrange rc \$sr\"; \
    if [ \"\$sr\" = 1 ]; then echo 'FAIL_PREFLOOR selrange' | tee -a /work/FAIL_PREFLOOR; rc=3; fi; fi; \
  if [ \$rc = 0 ] && [ $GOAL != synth ]; then \$M cts; rc=\$?; \
    C=\$(ls /work/run/results/asap7/*/base/4_cts.odb 2>/dev/null | head -1); \
    if [ \$rc = 0 ] && [ -n \"\$C\" ] && [ -f /work/hold_gate.tcl ]; then \
      S=\$(ls /work/run/results/asap7/*/base/4_cts.sdc 2>/dev/null | head -1); S=\${S:-/work/constraint.sdc}; \
      PLIBS=\"\$(\$M print-BC_LIB_FILES 2>/dev/null | sed -n 's/^BC_LIB_FILES *[:=] *//p')\" ODB=\$C SDC=\$S PLATFORM_DIR=/OpenROAD-flow-scripts/flow/platforms/asap7 \
        openroad -exit /work/hold_gate.tcl > /work/hold_gate.log 2>&1; grep OT_HOLD_GATE /work/hold_gate.log; \
      if grep -q 'OT_HOLD_GATE FAIL' /work/hold_gate.log; then grep OT_HOLD_GATE /work/hold_gate.log | sed 's/^/FAIL_POSTCTS /' | tee /work/FAIL_POSTCTS; rc=4; fi; fi; fi; \
  if [ \$rc = 0 ] && [ $GOAL != cts ] && [ $GOAL != synth ]; then \$M $GOAL; rc=\$?; fi; \
  if [ \$rc = 0 ] && [ $GOAL = finish ]; then \$M generate_abstract; rc=\$?; fi; fi; \
  R=\$(ls -d /work/run/results/asap7/*/base | head -1); \
  O=\$(ls \$R/5_route.odb \$R/6_final.odb 2>/dev/null | tail -1); \
  if [ -n \"\$O\" ]; then ODB=\$O PINS=/work/pins.json OUT=/work/pin_audit.json openroad -python -exit /work/pin_audit_core.py > /work/pin_audit.log 2>&1; fi; \
  if [ -f \$R/3_place.odb ]; then ODB=\$R/3_place.odb OUT=/work/placed.csv openroad -python -exit /work/dump_placed.py > /work/dump_placed.log 2>&1; cp \$R/ot_face_flops.txt /work/ 2>/dev/null; fi; \
  if [ -f \$R/6_final.odb ]; then \
    mkdir -p /work/views; \
    LIBS_TT=\$(\$M print-TC_LIB_FILES 2>/dev/null | sed -n 's/^TC_LIB_FILES *[:=] *//p' | sed 's/_SS_/_TT_/g; s/_FF_/_TT_/g; s/_ss\.lib/_tt.lib/g; s/_ff\.lib/_tt.lib/g'); \
    LEFS=\"\$(\$M print-TECH_LEF 2>/dev/null | sed -n 's/^TECH_LEF *[:=] *//p') \$(\$M print-SC_LEF 2>/dev/null | sed -n 's/^SC_LEF *[:=] *//p') \$(\$M print-ADDITIONAL_LEFS 2>/dev/null | sed -n 's/^ADDITIONAL_LEFS *[:=] *//p')\"; \
    echo \"LIBS_TT=\$LIBS_TT\" > /work/views/libs.txt; \
    for c in ff tt; do \
      case \$c in tt) L=\$LIBS_TT;; ff) L=\$(echo \$LIBS_TT | sed 's/_TT_/_FF_/g; s/_tt\.lib/_ff.lib/g');; ss) L=\$(echo \$LIBS_TT | sed 's/_TT_/_SS_/g; s/_tt\.lib/_ss.lib/g');; esac; \
      echo \"LIBS_\$c=\$L\" >> /work/views/libs.txt; \
      OT_CORNER=\$c OT_LIBS=\"\$L\" OT_LEFS=\"\$LEFS\" RES=\$R OT_MOD=\$(sed -n 's/^export DESIGN_NAME = //p' /work/config.mk) OT_OUT=/work/views OT_PER=\$(sed -n 's/^create_clock -name clk -period \([0-9.]*\).*/\1/p' /work/constraint.sdc) \
        openroad -exit /work/corners_hbm.tcl > /work/views/corner_\$c.log 2>&1 || rc=\$((rc+100)); \
    done; \
    cp \$R/*.lef /work/views/ 2>/dev/null; \
  fi; \
  chown -R \$HUID:\$HGID /work; exit \$rc" > "$K/run_$GOAL.log" 2>&1
rc=$?
$DK run --rm -v "$K":/work "$IMAGE" chown -R $(id -u):$(id -g) /work >/dev/null 2>&1
tail -5 "$K/run_$GOAL.log"
# signoff whenever the flow itself finished (a corners/ETM error is rc >= 100 and must not hide the verdict)
if { [ "$GOAL" = finish ] || [ "$GOAL" = post ]; } && [ $((rc % 100)) = 0 ] && ls "$K"/run/results/asap7/*/base/6_final.odb >/dev/null 2>&1; then
  SO="$K/signoff"
  [ ! -e "$SO/signoff.json" ] || SO="$K/signoff_$(date +%Y%m%d_%H%M%S)"
  python3 "$K/signoff.py" run --run-dir "$K/run" --kit "$K" --corners tt,ff --out "$SO" --docker "$DK" || rc=1
fi
exit $rc
