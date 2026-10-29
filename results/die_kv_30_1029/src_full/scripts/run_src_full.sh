#!/bin/bash
# DIE-KV-30-SRC: clean fresh KV source rebuild from full clock+provider union abstracts.
# Identical to codex-kv-0822 run_native_source.sh + run_import.sh except:
#  - /work/abstracts = codex-kv-0822/full_abstracts/*.lef (56 types)
#  - all outputs under die-kv-30-1029/src_full (Codex dir mounted read-only)
#  - preflight re-run on the SAME placements (proposal_open) against the NEW fresh constraints
set -euo pipefail
C=/srv/opentallas-scratch2/claude/codex-kv-0822
N=/srv/opentallas-scratch2/claude/die-kv-30-1029/src_full
W=/srv/opentallas-scratch2/claude/wt/die-kv-29
P=/srv/opentallas-scratch2/claude/die-kv-29-1029/venv/bin/python3
STAGE=${1:-all}
if [ "$STAGE" = all ] || [ "$STAGE" = source ]; then
docker run --rm --name dkv30-src-full --memory=32g --cpus=8 -e CORNER=TT -e LIBDIR=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM -v "$N/source_kit:/work:ro" -v "$N/native_source:/out" -v "$C:/r:ro" -v "$N:/n" -v "$W:/wt:ro" openroad/orfs:latest bash -lc 'set -e; source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -no_init -threads 8 -exit /out/source.tcl > /out/source.log 2>&1; openroad -python -no_init -exit /r/bind_native_source.py --source /out/fresh_source.odb --packed-tree /r/packed_tree.json --mapped /r/provider_mapped_kv6.json --clock-bindings /r/imp/bindings_clock.json --endpoints /out/native_endpoints.json --out /n/native_bound > /n/native_bound/bind.log 2>&1; openroad -python -no_init -exit /r/imp/export_constraints.py --source /n/native_bound/native_source.odb --inventory /r/provider_cells_kv6.json --die-plan /r/plan_e27f.json --tools /wt/tools/die_plan --out /n/native_bound/constraints > /n/native_bound/export.log 2>&1; chown -R 1000:1000 /out /n/native_bound'
python3 "$N/pin_source_hash.py" "$N"
$P "$C/imp/preflight.py" --inventory "$C/provider_cells_kv6.json" --mapped "$C/provider_mapped_kv6.json" --placements "$C/proposal_open/placements.json" --proposal-constraints "$C/native_bound/planning_constraints.json" --fresh-constraints "$N/native_bound/constraints/constraints.json" --bindings "$N/native_bound/bindings_native.json" --out "$N/native_bound/preflight_open.json" > "$N/native_bound/preflight_open.log" 2>&1
fi
if [ "$STAGE" = all ] || [ "$STAGE" = import ]; then
test -f "$N/review.md"
docker run --rm --name dkv30-src-import --memory=32g --cpus=8 -v "$C:/r:ro" -v "$N:/n" openroad/orfs:latest bash -lc 'set -e; source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -python -no_init -exit /r/imp/apply_cells.py --source /n/native_bound/native_source.odb --inventory /r/provider_cells_kv6.json --mapped /r/provider_mapped_kv6.json --placements /r/proposal_open/placements.json --bindings /n/native_bound/bindings_native.json --preflight /n/native_bound/preflight_open.json --review /n/review.md --out /n/imported > /n/imported/import.log 2>&1; openroad -python -no_init -exit /r/actual_reach.py --source /n/imported/provider.odb --mapped /r/provider_mapped_kv6.json --inventory /r/provider_cells_kv6.json --bindings /n/native_bound/bindings_native.json --out /n/imported/actual_reach.json > /n/imported/actual_reach.log 2>&1; chown -R 1000:1000 /n/imported'
fi
