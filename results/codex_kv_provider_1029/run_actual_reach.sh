#!/bin/bash
set -euo pipefail
R=/srv/opentallas-scratch2/claude/codex-kv-0822
docker run --rm --name codex-kv0822-reach --memory=24g --cpus=4 -v "$R:/r" openroad/orfs:latest bash -lc 'set -e; source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -python -no_init -exit /r/actual_reach.py --source /r/imported/provider.odb --mapped /r/provider_mapped_kv6.json --inventory /r/provider_cells_kv6.json --bindings /r/native_bound/bindings_native.json --out /r/imported/actual_reach.json > /r/imported/actual_reach.log 2>&1; chown -R 1000:1000 /r/imported'
