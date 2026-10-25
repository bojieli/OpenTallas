#!/bin/bash
# KVG3-CORES (gen_core_kit_kv.py): run one KV core kit through ORFS in docker: synth .. finish (TC), generate_abstract,
# RTL lint (rtl_lint.py, FAIL_PREFLOOR lint rc 8) and sdc_lint gate (CP1-R10, fail-closed) before synth, the DONT_USE-honouring adder map (adder_map_dontuse.py gen, ruling 4
# 10-25) before synth and its DONT_USE netlist check after synth (fail-closed), FF-only GRT hold repair in the FF vclk frame before the goal (FLOW-FIX 10-25, core_flow.py), typed face_guard gates after synth and synth ODB export,
# LEC (lec.py, 10-24) after the synth ODB gate: NOT EQUIVALENT stops the kit, UNPROVEN is recorded in lec/lec.json,
# pin audit of the routed ODB, then corners.tcl at TT / FF (STA + write_timing_model), then signoff.py (SIGNED = closed).  Outputs chowned back.
#   GOAL: finish (full ORFS finish incl. GDS merge: needs every macro GDS) | route (route + do-finish + abstract, no GDS
#   merge: cores with SRAM macros whose GDS is missing) | place (review stop) | post (existing 6_final.odb: abstract,
#   pin audit, corners, signoff only)
#   run_kit_kv.sh KITDIR [GOAL=finish] [MEM_GB=32] [CPUS=16]     (heavy: call it through ot-run --mem MEM_GB)
set -uo pipefail
# CLOCK-RESET 10-25: `make cts` (kit corners tc+bc) BEFORE the FF-only `make grt CORNERS=bc`: make builds every missing
# prerequisite, so without it floorplan..CTS repair ran on FF libraries only and TT setup was never repaired (canary -222.85).
K=$(cd "$1" && pwd); GOAL=${2:-finish}; MEM=${3:-32}; CPUS=${4:-16}
IMAGE=${OT_ORFS_IMAGE:-openroad/orfs:asap7lock}
DK=docker; docker ps >/dev/null 2>&1 || DK="sudo docker"
NAME=kvcore-$(basename "$K" | tr -c 'A-Za-z0-9_.-' _ | cut -c1-60)-$$
$DK run --rm --name "$NAME" --cpus="$CPUS" --memory="${MEM}g" --memory-swap="${MEM}g" -v "$K":/work \
  -e HUID=$(id -u) -e HGID=$(id -g) -w /OpenROAD-flow-scripts/flow "$IMAGE" bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; \
  M='make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=$CPUS'; \
  rc=0; if [ $GOAL != post ] && [ -f /work/rtl_lint.py ]; then python3 -I /work/rtl_lint.py /work > /work/rtl_lint.log 2>&1; rc=\$?; tail -3 /work/rtl_lint.log; if [ \$rc != 0 ]; then echo 'FAIL_PREFLOOR lint (implicit / undriven nets, missing module or port; or NOT RUN), see rtl_lint.json' | tee -a /work/FAIL_PREFLOOR; rc=8; fi; fi; \
  if [ \$rc = 0 ]; then python3 -I /work/sdc_lint.py /work --liberty \$(ls /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_*RVT_*.lib* 2>/dev/null | grep -v FAKE) > /work/sdc_lint.log 2>&1; rc=\$?; tail -3 /work/sdc_lint.log; fi; \
  if [ \$rc = 0 ] && [ $GOAL != post ]; then python3 -I /work/selrange_gate.py /work --out /work/selrange.json > /work/selrange.log 2>&1; src=\$?; tail -3 /work/selrange.log; if [ \$src = 1 ]; then rc=1; elif [ \$src != 0 ]; then echo \"SELRANGE NOT RUN (frontend cannot elaborate; see selrange.log)\"; fi; fi; \
  PD=/OpenROAD-flow-scripts/flow/platforms/asap7; \
  if [ \$rc = 0 ] && [ $GOAL != post ] && grep -q '^export ADDER_MAP_FILE = /work/adder_map_dontuse.v' /work/config.mk; then python3 -I /work/adder_map_dontuse.py gen --platform-dir \$PD --out /work/adder_map_dontuse.v --report /work/adder_map_dontuse.json; rc=\$?; fi; \
  if [ \$rc = 0 ] && [ $GOAL != post ]; then \$M synth; rc=\$?; fi; \
  N=\$(ls /work/run/results/asap7/*/base/1_2_yosys.v 2>/dev/null | tail -1); \
  if [ \$rc = 0 ] && [ $GOAL != post ] && [ -f /work/adder_map_dontuse.py ]; then python3 -I /work/adder_map_dontuse.py check --platform-dir \$PD --netlist \$N --report /work/dont_use_check.json; rc=\$?; fi; \
  if [ \$rc = 0 ] && [ $GOAL != post ]; then python3 -I /work/core_preflight.py /work \$N --out /work/face_guard.json > /work/face_guard.log 2>&1; rc=\$?; tail -3 /work/face_guard.log; fi; \
  D=\$(ls /work/run/results/asap7/*/base/1_synth.odb 2>/dev/null | tail -1); \
  if [ \$rc = 0 ] && [ $GOAL != post ]; then \
    test -n \"\$D\" || rc=103; \
    if [ \$rc = 0 ]; then printf 'read_db %s\\nwrite_verilog /work/1_synth_odb.v\\n' \$D > /work/synth_odb_v.tcl; openroad -exit /work/synth_odb_v.tcl > /work/synth_odb_v.log 2>&1; rc=\$?; fi; \
    if [ \$rc = 0 ]; then python3 -I /work/core_preflight.py /work /work/1_synth_odb.v --out /work/face_guard_odb.json > /work/face_guard_odb.log 2>&1; rc=\$?; tail -3 /work/face_guard_odb.log; fi; \
  fi; \
  if [ \$rc = 0 ] && [ $GOAL != post ] && [ -f /work/lec.py ] && [ -n \"\$N\" ]; then python3 -I /work/lec.py /work --netlist \$N --out /work/lec > /work/lec_run.log 2>&1; lr=\$?; tail -1 /work/lec_run.log; \
    if [ \$lr = 1 ]; then echo 'LEC NOT EQUIVALENT: the kit stops (lec/lec.json)'; rc=1; elif [ \$lr != 0 ]; then echo \"LEC WARNING (exit \$lr): not proved, recorded in lec/lec.json; the flow continues\"; fi; fi; \
  HM=\$(sed -n 's/^export OT_HOLD_FF_MARGIN = //p' /work/config.mk); VF=\$(sed -n 's/^export OT_VCLK_FF = //p' /work/config.mk); if [ \$rc = 0 ] && [ -n \"\$HM\" ] && [ -n \"\$VF\" ] && { [ $GOAL = finish ] || [ $GOAL = route ]; }; then \$M cts; rc=\$?; if [ \$rc = 0 ]; then OT_VCLK_CORNER=ff \$M grt CORNER=BC CORNERS=bc HOLD_SLACK_MARGIN=\$HM; rc=\$?; fi; if [ \$rc != 0 ]; then echo 'FF-only GRT hold repair (FF vclk frame) failed'; fi; fi; \
  if [ \$rc = 0 ] && [ $GOAL != post ]; then \$M $GOAL; rc=\$?; fi; \
  if [ \$rc = 0 ] && [ $GOAL = route ]; then \$M do-finish; rc=\$?; fi; \
  if [ \$rc = 0 ] && { [ $GOAL = finish ] || [ $GOAL = route ] || [ $GOAL = post ]; }; then \$M do-generate_abstract; rc=\$?; fi; \
  R=\$(ls -d /work/run/results/asap7/*/base | head -1); \
  O=\$(ls \$R/5_route.odb \$R/6_final.odb 2>/dev/null | tail -1); \
  if [ -n \"\$O\" ]; then ODB=\$O PINS=/work/pins.json OUT=/work/pin_audit.json openroad -python -exit /work/pin_audit_core.py; fi; \
  if [ \$rc = 0 ] && [ -f \$R/6_final.odb ]; then \
    mkdir -p /work/views; \
    LIBS_TT=\$(\$M print-LIB_FILES 2>/dev/null | sed -n 's/^LIB_FILES[:=] *//p'); \
    LEFS=\"\$(\$M print-TECH_LEF 2>/dev/null | sed -n 's/^TECH_LEF[:=] *//p') \$(\$M print-SC_LEF 2>/dev/null | sed -n 's/^SC_LEF[:=] *//p') \$(\$M print-ADDITIONAL_LEFS 2>/dev/null | sed -n 's/^ADDITIONAL_LEFS[:=] *//p')\"; \
    echo \"LIBS_TT=\$LIBS_TT\" > /work/views/libs.txt; \
    test -n \"\$LIBS_TT\" || { echo \"ERROR: empty LIB_FILES from ORFS make print helper\"; exit 102; }; \
    for c in tt ff; do \
      case \$c in tt) L=\$LIBS_TT;; ff) L=\$(echo \$LIBS_TT | sed 's/_TT_/_FF_/g; s/_tt\.lib/_ff.lib/g');; esac; \
      echo \"LIBS_\$c=\$L\" >> /work/views/libs.txt; \
      OT_CORNER=\$c OT_LIBS=\"\$L\" OT_LEFS=\"\$LEFS\" RES=\$R OT_MOD=\$(sed -n 's/^export DESIGN_NAME = //p' /work/config.mk) OT_OUT=/work/views \
        openroad -exit /work/corners.tcl > /work/views/corner_\$c.log 2>&1 || rc=\$((rc+100)); \
    done; \
    cp \$R/*.lef /work/views/ 2>/dev/null; \
  fi; \
  chown -R \$HUID:\$HGID /work; exit \$rc" > "$K/run_$GOAL.log" 2>&1
rc=$?
$DK run --rm -v "$K":/work "$IMAGE" chown -R $(id -u):$(id -g) /work >/dev/null 2>&1
tail -5 "$K/run_$GOAL.log"
# SIGNOFF (coordinator 10-24, main f942bf2f72): uniform tools/die_plan/signoff.py verdict (TT setup / FF hold with the
# standard boundary-hold overlay / DRV / unconstrained / pin-flop spread / sdc_lint / face_guard / DRC + antenna) in
# KIT/signoff/signoff.json; a core is closed only when it says SIGNED (collect_core.py reads it).
if [ $rc = 0 ] && { [ $GOAL = finish ] || [ $GOAL = route ] || [ $GOAL = post ]; } && [ -f "$K/signoff.py" ]; then
  SIGNOFF_DOCKER=${SIGNOFF_DOCKER:-$DK} python3 -I "$K/signoff.py" run --run-dir "$K/run" --kit "$K" \
    --out "$K/signoff" --image "$IMAGE" > "$K/signoff.log" 2>&1
  rc=$?
  grep -E '^SIGNOFF|^  - ' "$K/signoff.log" | head -12
fi
exit $rc
