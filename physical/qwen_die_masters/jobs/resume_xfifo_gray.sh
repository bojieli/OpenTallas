#!/bin/bash
# J6 approved config-only continuation. Daemon admission/current helper shipping is required.
# Only the fresh run is written; the frozen failed source/checkpoints stay read-only.
set -euo pipefail
SRC=${SRC:?}; RUN=${1:?}; LABEL=${2:?}
OLD=/srv/opentallas-scratch2/scratch/claude/closure-loop/qfd_io_xfifo_p2-1d3c576bbtc/routes/qfd_io_xfifo_p2_1d3c576bbtc/work/orfs
W=$RUN/routes/$LABEL
O=$W/work/orfs
mkdir -p "$W"
if [ ! -f "$W/checkpoint_import.json" ]; then
  python3 "$SRC/physical/qwen_die_masters/jobs/stage_xfifo_gray.py" "$OLD" "$O" "$SRC" "$W"
fi
export OT_MM_FF_SDC=physical/qwen_die_masters/signoff/qfd_io_xfifo_p2_gray.sdc
# Current daemon ships orfs_hold_mm.py/.tcl before launch; same helpers as run_abi3_physical.
container_make() {
  docker run --rm -v "$SRC:/src:ro" -v "$O:/work" -w /OpenROAD-flow-scripts/flow \
    openroad/orfs:asap7lock bash -lc '
      trap '''chmod -R a+rwX /work >/dev/null 2>&1 || true''' EXIT
      source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
      python3 /src/tools/orfs_hold_mm.py /OpenROAD-flow-scripts/flow/scripts
      python3 /src/tools/orfs_allcorner_spef.py /OpenROAD-flow-scripts/flow/scripts/final_outputs.tcl
      make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work FLOW_VARIANT=base NUM_CORES=16 "$@"
    ' -- "$@"
}
# Updated config intentionally changes only CTS/next-stage constraints. Pin the
# immutable completed placement targets so make never redoes source/floorplan.
B=$(find "$O/results/asap7" -type d -name base -print -quit)
DESIGN=$(basename "$(dirname "$B")")
PIN_ODB=/work/results/asap7/$DESIGN/base/3_place.odb
PIN_SDC=/work/results/asap7/$DESIGN/base/3_place.sdc
container_make -n -o "$PIN_ODB" -o "$PIN_SDC" cts > "$W/resume_dryrun.log" 2>&1
python3 - "$W/resume_dryrun.log" <<'PY2'
import pathlib,re,sys
s=pathlib.Path(sys.argv[1]).read_text(); stages=sorted(set(re.findall(r"do-([0-9]_[0-9]_[a-z_]+)",s)))
assert stages==['4_1_cts'], 'unexpected resume stages '+repr(stages)
print('RESUME_FROM=4_1_cts; completed placement pinned')
PY2
# Separate CTS then route goals avoid make -n's absent future GRT SDC side effect.
container_make -o "$PIN_ODB" -o "$PIN_SDC" cts > "$W/flow_cts.log" 2>&1
container_make -o "$PIN_ODB" -o "$PIN_SDC" finish > "$W/flow_finish.log" 2>&1
printf 'flow_rc=0\n' > "$W/status"
cat "$SRC/physical/qwen_die_masters/signoff/qfd_io_xfifo_p2.sdc" \
    "$SRC/physical/qwen_die_masters/signoff/qfd_io_xfifo_gray_cdc.tcl" > "$W/signoff.sdc"
python3 "$SRC/tools/w18/corner_sta_ref.py" --orfs-dir "$O" --extra-sdc "$W/signoff.sdc" \
  --output "$W/corner_sta.json" > "$W/sta.log" 2>&1
printf 'corner_rc=0\n' >> "$W/status"
