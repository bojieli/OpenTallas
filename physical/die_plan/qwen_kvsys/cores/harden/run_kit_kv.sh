#!/bin/bash
# KVG3-CORES (gen_core_kit_kv.py): run one KV core kit through ORFS in docker: synth .. finish (TC), generate_abstract,
# sdc_lint gate (CP1-R10, fail-closed) before synth, typed face_guard gates after synth and synth ODB export,
# LEC (lec.py, 10-24) after the synth ODB gate: NOT EQUIVALENT stops the kit, UNPROVEN is recorded in lec/lec.json,
# pin audit of the routed ODB, then corners.tcl at TT / FF (STA + write_timing_model), then signoff.py (SIGNED = closed).  Outputs chowned back.
#   GOAL: finish (full ORFS finish incl. GDS merge: needs every macro GDS) | route (route + do-finish + abstract, no GDS
#   merge: cores with SRAM macros whose GDS is missing) | place (review stop) | post (existing 6_final.odb: abstract,
#   pin audit, corners, signoff only)
#   run_kit_kv.sh KITDIR [GOAL=finish] [MEM_GB=32] [CPUS=16]     (heavy: call it through ot-run --mem MEM_GB)
set -uo pipefail
K=$(cd "$1" && pwd); GOAL=${2:-finish}; MEM=${3:-32}; CPUS=${4:-16}
IMAGE=${OT_ORFS_IMAGE:-openroad/orfs:asap7lock}
DK=docker; docker ps >/dev/null 2>&1 || DK="sudo docker"
NAME=kvcore-$(basename "$K" | tr -c 'A-Za-z0-9_.-' _ | cut -c1-60)-$$
$DK run --rm --name "$NAME" --cpus="$CPUS" --memory="${MEM}g" --memory-swap="${MEM}g" -v "$K":/work \
  -e HUID=$(id -u) -e HGID=$(id -g) -w /OpenROAD-flow-scripts/flow "$IMAGE" bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; \
  M='make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=$CPUS'; \
  rc=0; python3 -I /work/sdc_lint.py /work --liberty \$(ls /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_*RVT_*.lib* 2>/dev/null | grep -v FAKE) > /work/sdc_lint.log 2>&1; rc=\$?; tail -3 /work/sdc_lint.log; \
  if [ \$rc = 0 ] && [ $GOAL != post ]; then python3 -I /work/selrange_gate.py /work --out /work/selrange.json > /work/selrange.log 2>&1; src=\$?; tail -3 /work/selrange.log; if [ \$src = 1 ]; then rc=1; elif [ \$src != 0 ]; then echo \"SELRANGE NOT RUN (frontend cannot elaborate; see selrange.log)\"; fi; fi; \
  if [ \$rc = 0 ] && [ $GOAL != post ]; then \$M synth; rc=\$?; fi; \
  N=\$(ls /work/run/results/asap7/*/base/1_2_yosys.v 2>/dev/null | tail -1); \
  if [ \$rc = 0 ] && [ $GOAL != post ]; then python3 -I /work/core_preflight.py /work \$N --out /work/face_guard.json > /work/face_guard.log 2>&1; rc=\$?; tail -3 /work/face_guard.log; fi; \
  D=\$(ls /work/run/results/asap7/*/base/1_synth.odb 2>/dev/null | tail -1); \
  if [ \$rc = 0 ] && [ $GOAL != post ]; then \
    test -n \"\$D\" || rc=103; \
    if [ \$rc = 0 ]; then printf 'read_db %s\\nwrite_verilog /work/1_synth_odb.v\\n' \$D > /work/synth_odb_v.tcl; openroad -exit /work/synth_odb_v.tcl > /work/synth_odb_v.log 2>&1; rc=\$?; fi; \
    if [ \$rc = 0 ]; then python3 -I /work/core_preflight.py /work /work/1_synth_odb.v --out /work/face_guard_odb.json > /work/face_guard_odb.log 2>&1; rc=\$?; tail -3 /work/face_guard_odb.log; fi; \
  fi; \
  if [ \$rc = 0 ] && [ $GOAL != post ] && [ -f /work/lec.py ] && [ -n \"\$N\" ]; then python3 -I /work/lec.py /work --netlist \$N --out /work/lec > /work/lec_run.log 2>&1; lr=\$?; tail -1 /work/lec_run.log; \
    if [ \$lr = 1 ]; then echo 'LEC NOT EQUIVALENT: the kit stops (lec/lec.json)'; rc=1; elif [ \$lr != 0 ]; then echo \"LEC WARNING (exit \$lr): not proved, recorded in lec/lec.json; the flow continues\"; fi; fi; \
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
