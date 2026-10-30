#!/bin/bash
set -euo pipefail
P=/srv/opentallas-scratch2/claude/codex-head-residual-1030
K=$P/tile3_dpl
O=$P/tile4_dump
mkdir -p "$O"
cp "$P/geomtools/geom_dump.tcl" "$O/"
printf 'read_db /work/diag_out6/3_place.odb\nsource /out/geom_dump.tcl\n' > "$O/dump.tcl"
docker run --rm --name codex-head-tile4-dump --cpus=2 --memory=8g --memory-swap=8g -v "$K":/work:ro -v "$O":/out -e OT_GEOM_OUT=/out/geom.tsv -w /out openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -exit /out/dump.tcl'
python3 "$P/export_root_bins.py" "$P/geomtools" "$O/geom.tsv" "$O/hd_tile_core_root_bins.json"
