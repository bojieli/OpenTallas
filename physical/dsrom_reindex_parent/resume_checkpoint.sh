#!/bin/bash
# Only a failed run may be copied here; no source, constraints, or checkpoint in BASE is changed.
set -euo pipefail
BASE=${1:?failed route directory}; OUT=${2:?fresh successor directory}; SRC=${3:?pinned archive root}
test ! -e "$OUT"
test "$(cat "$BASE/exit")" != 0
# Inventory and headroom are recorded before copying; no repeated synthesis.
mkdir -p "$OUT/work"
{ free -g; df -h "$BASE"; du -sh "$BASE/work/orfs"; } > "$OUT/headroom.txt"
cp -a --reflink=auto "$BASE/work/orfs" "$OUT/work/orfs"
W=$OUT/work/orfs
B=$(find "$W/results/asap7" -mindepth 2 -maxdepth 2 -type d -name base)
test -f "$B/2_1_floorplan.odb"
test -f "$B/1_2_yosys.v"
sha256sum "$B/2_1_floorplan.odb" "$B/1_2_yosys.v" "$W/constraint.sdc" > "$OUT/reused_sha256.txt"
# The explicit full-shape grid replaces the automatic placer. The same fixed hook
# already passed on the actual full-shape 2_1 database, including all pin tracks.
cat >> "$W/config.mk" <<'CFG'
export MACRO_PLACEMENT_TCL = /src/physical/dsrom_reindex_parent/place.tcl
export POST_MACRO_PLACE_TCL =
CFG
set +e
docker run --rm -v "$SRC:/src:ro" -v "$W:/work" -w /OpenROAD-flow-scripts/flow \
  openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; python3 /src/tools/orfs_allcorner_spef.py /OpenROAD-flow-scripts/flow/scripts/final_outputs.tcl && make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work FLOW_VARIANT=base NUM_CORES=16 finish metadata-generate' > "$OUT/resume.log" 2>&1
rc=$?
printf '%s\n' "$rc" > "$OUT/route.exit"
set -e
if [ "$rc" -eq 0 ]; then
  cd "$SRC"
  python3 tools/w18/corner_sta.py --orfs-dir "$W" \
    --macro physical/asap7_memory_macros/ot_sram_1r1w_512x128_m4_r2c2 \
    --post-sdc physical/dsrom_reindex_parent/signoff_833.sdc --output "$OUT/corner_sta.json" > "$OUT/signoff.log" 2>&1
fi
printf '%s\n' "$rc" > "$OUT/terminal.exit"
exit "$rc"
