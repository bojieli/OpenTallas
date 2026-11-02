#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
test -s input.odb
exec docker run --rm --memory=8g --memory-swap=8g --cpus=2 -v "$PWD":/work -w /work sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29 bash -lc 'set -euo pipefail; source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -exit /work/read_geom.tcl' > geom_dump.log 2>&1
