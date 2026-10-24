#!/bin/bash
# KVG3-CORES (gen_core_kit_kv.py): run one KV core kit through ORFS in docker: synth .. finish (TC), generate_abstract,
# sdc_lint gate (CP1-R10, fail-closed) before synth, face_guard after synth (REPORT ONLY for cores),
# pin audit of the routed ODB, then corners.tcl at TT / FF / SS (STA + write_timing_model).  Outputs chowned back.
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
  if [ \$rc = 0 ]; then \$M synth; rc=\$?; fi; \
  N=\$(ls /work/run/results/asap7/*/base/1_2_yosys.v 2>/dev/null | tail -1); \
  if [ \$rc = 0 ]; then python3 -I /work/face_guard.py \$N --pins /work/pins.json --out /work/face_guard.json > /work/face_guard.log 2>&1; echo \"face_guard rc \$? (report only: core pins are leaf pins, not planned face registers)\"; fi; \
  if [ \$rc = 0 ]; then \$M $GOAL; rc=\$?; fi; \
  if [ \$rc = 0 ] && [ $GOAL = finish ]; then \$M generate_abstract; rc=\$?; fi; \
  R=\$(ls -d /work/run/results/asap7/*/base | head -1); \
  O=\$(ls \$R/5_route.odb \$R/6_final.odb 2>/dev/null | tail -1); \
  if [ -n \"\$O\" ]; then ODB=\$O PINS=/work/pins.json OUT=/work/pin_audit.json openroad -python -exit /work/pin_audit_core.py; fi; \
  if [ \$rc = 0 ] && [ -f \$R/6_final.odb ]; then \
    mkdir -p /work/views; \
    LIBS_TT=\$(\$M print-LIB_FILES 2>/dev/null | sed -n 's/^LIB_FILES = //p'); \
    LEFS=\"\$(\$M print-TECH_LEF 2>/dev/null | sed -n 's/^TECH_LEF = //p') \$(\$M print-SC_LEF 2>/dev/null | sed -n 's/^SC_LEF = //p') \$(\$M print-ADDITIONAL_LEFS 2>/dev/null | sed -n 's/^ADDITIONAL_LEFS = //p')\"; \
    echo \"LIBS_TT=\$LIBS_TT\" > /work/views/libs.txt; \
    for c in tt ff ss; do \
      case \$c in tt) L=\$LIBS_TT;; ff) L=\$(echo \$LIBS_TT | sed 's/_TT_/_FF_/g; s/_tt\.lib/_ff.lib/g');; ss) L=\$(echo \$LIBS_TT | sed 's/_TT_/_SS_/g; s/_tt\.lib/_ss.lib/g');; esac; \
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
exit $rc
