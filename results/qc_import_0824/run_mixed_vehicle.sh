#!/bin/bash
set -euo pipefail
Q=/srv/opentallas-scratch2/claude
R=$Q/codex-qc-import-0824
W=$Q/wt/codex-qc-import-0824
mkdir -p "$R/reachfix/mixed_import_vehicle"
docker run --rm --name codex-qci-mixed-vehicle-$$ --memory=32g --memory-swap=32g --cpus=4 -v "$Q:$Q" -w "$R" -e PYTHONPATH="$R/pydeps" openroad/orfs:asap7lock bash -c "set -e; source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; trap 'chown -R 1000:1000 $R/reachfix/mixed_import_vehicle' EXIT; openroad -python -exit $R/src/mixed_import_vehicle.py --root $R --tools $W/tools/die_plan > $R/reachfix/mixed_import_vehicle/run.log 2>&1"
tail -20 "$R/reachfix/mixed_import_vehicle/run.log"
