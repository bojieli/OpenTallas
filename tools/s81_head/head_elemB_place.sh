#!/bin/bash
# HEAD-CORE-LAT-R5 /ELEMB: synth + place only (geometry for head_tree_plan.py), same docker/ORFS image as run_kit.sh.
# Gates kept: sdc_lint before synth, face_guard on the Yosys netlist after synth (fail-closed). Then the 12.2a1
# pushdown netlist patch (patch_synth.tcl), the post-patch SDC, make place, geo dump (dump_geo_head.tcl).
set -uo pipefail
K=$(realpath "$1"); MEM=${2:-32}; CPUS=${3:-16}
IMAGE=openroad/orfs:asap7lock
TOP=$(sed -n 's/^export DESIGN_NAME = //p' "$K/config.mk")
SKIP=$(cat "$K/face_guard_skip.txt")
echo "image $IMAGE $(docker image inspect --format '{{.Id}}' $IMAGE) host $(hostname) start $(date -Is)" > "$K/image.txt"
docker run --rm --name hcl5-elemB-$$ --cpus="$CPUS" --memory="${MEM}g" --memory-swap="${MEM}g" -v "$K":/work \
  -e HUID=$(id -u) -e HGID=$(id -g) -w /OpenROAD-flow-scripts/flow "$IMAGE" bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; \
  M='make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=$CPUS'; rc=0; \
  R=/work/run/results/asap7/\$(sed -n 's/^export DESIGN_NICKNAME = //p' /work/config.mk)/base; \
  python3 -I /work/sdc_lint.py /work --liberty \$(ls /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_*RVT_*.lib* | grep -v FAKE) > /work/sdc_lint.log 2>&1; rc=\$?; echo SDC_LINT rc \$rc; \
  if [ \$rc = 0 ]; then python3 -I /work/orfs_hold_mm.py /OpenROAD-flow-scripts/flow/scripts /work/orfs_hold_mm.tcl > /work/orfs_hold_mm.log 2>&1; rc=\$?; grep -q 'status.: .patched.' /work/orfs_hold_mm.log || rc=3; fi; \
  if [ \$rc = 0 ]; then \$M synth; rc=\$?; echo SYNTH rc \$rc; fi; \
  if [ \$rc = 0 ]; then python3 -I /work/face_guard_core.py \$R/1_2_yosys.v $TOP '$SKIP' /work/pins.json /work/face_guard.json; rc=\$?; echo FACE_GUARD rc \$rc; fi; \
  if [ \$rc = 0 ]; then cp \$R/1_2_yosys.v /work/netlist_1_2_yosys.v; ODB_IN=\$R/1_synth.odb openroad -exit /work/patch_synth.tcl; rc=\$?; echo PATCH rc \$rc; \
    cp /work/constraint_pd.sdc \$R/1_synth.sdc; touch \$R/1_synth.odb \$R/1_synth.sdc; fi; \
  if [ \$rc = 0 ]; then \$M place; rc=\$?; echo PLACE rc \$rc; fi; \
  if [ \$rc = 0 ]; then ODB=\$R/3_place.odb OUT=/work/elemB_r5_3place.geo openroad -exit /work/dump_geo_head.tcl; rc=\$?; fi; \
  chown -R \$HUID:\$HGID /work; echo FLOW rc \$rc; exit \$rc" > "$K/trial.log" 2>&1
rc=$?
echo "end $(date -Is) rc $rc" >> "$K/image.txt"
exit $rc
