#!/bin/bash
set -euo pipefail
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
trap 'chown -R 1000:1000 /out' EXIT
openroad -python -exit /graft.py --source /in/clock_unrouted.odb --target /in/target_signal.odb --tree /tree.json --out /out/clock_grafted.odb --report /out/endpoints.json
