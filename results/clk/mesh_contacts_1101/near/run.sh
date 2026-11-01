#!/bin/bash
set -euo pipefail
O=$(cd "$(dirname "$0")" && pwd)
docker run --rm --name codex-hbm-$(basename "$O") --memory=4g --memory-swap=4g --cpus=4 -v "$O:/o" openroad/orfs:asap7lock bash -lc 'set -e; source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -no_init -threads 4 -exit /o/mesh_contact_route.tcl > /o/route.log 2>&1'
