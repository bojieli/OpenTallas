#!/bin/bash
# DIE-KV-31-SRC: KV source rebuild with the plan's VDDPHY interface on kv3_sys_c_part (phy_pg_abstracts.py).
# Identical to DIE-KV-30-SRC run_src_full.sh + run_pg_grid.sh (same codex-kv-0822 inputs, same placements,
# same codex-kv-pg-0834 grid3 recipe and pdn_top.tcl) except /work/abstracts = src_phy/abstracts (only
# kv3_sys_c_part.lef differs: CORE VDD M7 cut at phy_sys_c_ucie, VDDPHY M7 inside). Stages: source | import (needs review.md).
set -euo pipefail
C=/srv/opentallas-scratch2/claude/codex-kv-0822
PGH=/srv/opentallas-scratch2/claude/codex-kv-pg-0834
N=/srv/opentallas-scratch2/claude/die-kv-31-1029/src_phy
W=/srv/opentallas-scratch2/claude/wt/die-kv-29
P=/srv/opentallas-scratch2/claude/die-kv-29-1029/venv/bin/python3
STAGE=${1:?source|import}
IMG=openroad/orfs:latest
if [ "$STAGE" = source ]; then
docker run --rm --name dkv31-src-phy --memory=32g --cpus=8 -e CORNER=TT -e LIBDIR=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM -v "$N/source_kit:/work:ro" -v "$N/native_source:/out" -v "$C:/r:ro" -v "$N:/n" -v "$W:/wt:ro" $IMG bash -lc 'set -e; source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -no_init -threads 8 -exit /out/source.tcl > /out/source.log 2>&1; openroad -python -no_init -exit /r/bind_native_source.py --source /out/fresh_source.odb --packed-tree /r/packed_tree.json --mapped /r/provider_mapped_kv6.json --clock-bindings /r/imp/bindings_clock.json --endpoints /out/native_endpoints.json --out /n/native_bound > /n/native_bound/bind.log 2>&1; openroad -python -no_init -exit /r/imp/export_constraints.py --source /n/native_bound/native_source.odb --inventory /r/provider_cells_kv6.json --die-plan /r/plan_e27f.json --tools /wt/tools/die_plan --out /n/native_bound/constraints > /n/native_bound/export.log 2>&1; openroad -python -no_init -exit /n/check_src.py --odb /n/native_bound/native_source.odb --out /n/receipts/check_native.json --hard /n/native_bound/constraints/constraints.json > /n/receipts/check_native.log 2>&1; chown -R 1000:1000 /out /n/native_bound /n/receipts'
python3 "$N/pin_source_hash.py" "$N"
$P "$C/imp/preflight.py" --inventory "$C/provider_cells_kv6.json" --mapped "$C/provider_mapped_kv6.json" --placements "$C/proposal_open/placements.json" --proposal-constraints "$C/native_bound/planning_constraints.json" --fresh-constraints "$N/native_bound/constraints/constraints.json" --bindings "$N/native_bound/bindings_native.json" --out "$N/native_bound/preflight_open.json" > "$N/native_bound/preflight_open.log" 2>&1
fi
if [ "$STAGE" = import ]; then
test -f "$N/review.md"
docker run --rm --name dkv31-src-phy-import --memory=96g --cpus=16 -v "$C:/r:ro" -v "$PGH:/p:ro" -v "$N:/n" $IMG bash -lc 'set -e; source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -python -no_init -exit /r/imp/apply_cells.py --source /n/native_bound/native_source.odb --inventory /r/provider_cells_kv6.json --mapped /r/provider_mapped_kv6.json --placements /r/proposal_open/placements.json --bindings /n/native_bound/bindings_native.json --preflight /n/native_bound/preflight_open.json --review /n/review.md --out /n/imported > /n/imported/import.log 2>&1; openroad -python -no_init -exit /r/actual_reach.py --source /n/imported/provider.odb --mapped /r/provider_mapped_kv6.json --inventory /r/provider_cells_kv6.json --bindings /n/native_bound/bindings_native.json --out /n/imported/actual_reach.json > /n/imported/actual_reach.log 2>&1; openroad -python -no_init -exit /p/src/prepare_grid.py --odb /n/imported/provider.odb --grid /p/grid/source_pg_reservations.json --out /n/pg_grid > /n/pg_grid/prepare.log 2>&1 && openroad -no_init -threads 16 -exit /n/pdn_top.tcl > /n/pg_grid/grid.log 2>&1 && openroad -python -no_init -exit /p/src/readback_grid.py --source /n/imported/provider.odb --target /n/pg_grid/native_grid.odb --out /n/pg_grid/readback.json > /n/pg_grid/readback.log 2>&1; openroad -python -no_init -exit /n/check_src.py --odb /n/pg_grid/native_grid.odb --out /n/receipts/check_grid.json --hard /n/native_bound/constraints/constraints.json > /n/receipts/check_grid.log 2>&1; chown -R 1000:1000 /n/imported /n/pg_grid /n/receipts'
fi
echo STAGE_DONE $STAGE $(date -Is)
