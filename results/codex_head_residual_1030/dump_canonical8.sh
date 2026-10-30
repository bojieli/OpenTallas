#!/bin/bash
set -euo pipefail
P=/srv/opentallas-scratch2/claude/codex-head-residual-1030
K=$P/tile_canonical8_dpl
O=$P/canonical8_dump
mkdir -p "$O"
cp "$P/geomtools/geom_dump.tcl" "$O/"
printf 'read_db /work/diag_canonical8/3_place.odb\nsource /out/geom_dump.tcl\n' > "$O/dump.tcl"
docker run --rm --name codex-head-canonical8-dump --cpus=2 --memory=8g --memory-swap=8g -v "$K":/work:ro -v "$O":/out -e OT_GEOM_OUT=/out/geom.tsv -w /out openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -exit /out/dump.tcl'
python3 "$P/export_root_bins.py" "$P/geomtools" "$O/geom.tsv" "$O/hd_tile_core_root_bins.json"
rc=0
python3 "$P/geomtools/geom_rules.py" "$O/geom.tsv" --json "$O/diagnostic_auto_geom.json" --outline 708.48x1036.8 --all-kits --max-layer M7 --land-slots "$K/land_slots.json" --face-guard "$K/face_guard.json" --title 'HEAD tile canonical8 existing boundary+reset leaf repair no route' || rc=$?
python3 "$P/geomtools/geom_png.py" "$O/geom.tsv" "$O/diagnostic_auto_geom.json" "$O/actual_canonical8.png"
exit "$rc"
