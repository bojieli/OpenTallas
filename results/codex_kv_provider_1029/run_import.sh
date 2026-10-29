#!/bin/bash
set -euo pipefail
R=/srv/opentallas-scratch2/claude/codex-kv-0822
mkdir -p "$R/imported"
docker run --rm --name codex-kv0822-provider-import --memory=32g --cpus=8 -v "$R:/r" openroad/orfs:latest bash -lc 'set -e; source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -python -no_init -exit /r/imp/apply_cells.py --source /r/native_bound/native_source.odb --inventory /r/provider_cells_kv6.json --mapped /r/provider_mapped_kv6.json --placements /r/proposal_open/placements.json --bindings /r/native_bound/bindings_native.json --preflight /r/native_bound/preflight_open.json --review /r/review.md --out /r/imported > /r/imported/import.log 2>&1; chown -R 1000:1000 /r/imported'
