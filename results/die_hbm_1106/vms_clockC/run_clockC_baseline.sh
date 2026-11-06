#!/usr/bin/env bash
set -euo pipefail
KIT=${1:?clock candidate kit required}
MEM=${2:-48}
CPUS=${3:-8}
IMAGE=${OT_ORFS_IMAGE:-openroad/orfs:asap7lock}
# The seed already contains fixed routes. This construction pass changes only clocks;
# ordinary routed signoff follows, then a fresh clock-frozen data ECO if required.
# Skip the incremental GRT repair adapter, which cannot rebuild untouched fixed-net trees.
grep -q "CLOCK_CONSTRUCTION PASS" "$KIT/clockC_construct.log"
NAME=codex-vms-clockC-$$
docker run --rm --name "$NAME" --cpus="$CPUS" --memory="${MEM}g" --memory-swap="${MEM}g" \
 -e NUM_CORES="$CPUS" -v "$KIT:/work" -w /OpenROAD-flow-scripts/flow "$IMAGE" bash -lc '
 source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
 python3 -I /work/orfs_hold_mm.py /OpenROAD-flow-scripts/flow/scripts --metrics-only > /work/orfs_metrics.log 2>&1 || exit 9
 python3 -I /work/orfs_hold_mm.py /OpenROAD-flow-scripts/flow/scripts /work/orfs_hold_mm.tcl > /work/orfs_hold_mm.log 2>&1 || exit 9
 make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES="$NUM_CORES" SKIP_INCREMENTAL_REPAIR=1 do-route > /work/clockC_route.log 2>&1
 rc=$?
 if [ "$rc" = 0 ]; then
  make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES="$NUM_CORES" do-finish > /work/clockC_finish.log 2>&1
  rc=$?
 fi
 chown -R 1000:1000 /work
 exit "$rc"
 '
bash "$KIT/run_kit_hbm.sh" "$KIT" post "$MEM" "$CPUS"
python3 -I "$KIT/lec.py" "$KIT" \
 --netlist "$KIT/run/results/asap7/hbc_hnx_vms_bank_q0_faces__vecd4ae/base/6_final.v" \
 --out "$KIT/lec_postroute" --image "$IMAGE" --mem 24 --jobs "$CPUS"
