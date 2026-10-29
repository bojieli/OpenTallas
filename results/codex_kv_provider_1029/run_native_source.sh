#!/bin/bash
set -euo pipefail
R=/srv/opentallas-scratch2/claude/codex-kv-0822
W=/srv/opentallas-scratch2/claude/wt/die-kv-29
mkdir -p "$R/native_bound"
docker run --rm --name codex-kv0822-native-source --memory=32g --cpus=8 -e CORNER=TT -e LIBDIR=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM -v "$R/source_kit:/work:ro" -v "$R/native_source:/out" -v "$R:/r" -v "$W:/wt:ro" openroad/orfs:latest bash -lc 'set -e; source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -no_init -threads 8 -exit /out/source.tcl > /r/native_source/source.log 2>&1; openroad -python -no_init -exit /r/bind_native_source.py --source /out/fresh_source.odb --packed-tree /r/packed_tree.json --mapped /r/provider_mapped_kv6.json --clock-bindings /r/imp/bindings_clock.json --endpoints /out/native_endpoints.json --out /r/native_bound > /r/native_bound/bind.log 2>&1; openroad -python -no_init -exit /r/imp/export_constraints.py --source /r/native_bound/native_source.odb --inventory /r/provider_cells_kv6.json --die-plan /r/plan_e27f.json --tools /wt/tools/die_plan --out /r/native_bound/constraints > /r/native_bound/export.log 2>&1; chown -R 1000:1000 /out /r/native_bound'
