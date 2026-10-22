#!/bin/bash
set -euo pipefail
docker run --rm --name kv-attn-physical-preflight-1019 -v "$PWD:/work" --entrypoint bash openroad/orfs:asap7lock -lc 'source /OpenROAD-flow-scripts/env.sh; openroad -exit /work/place.tcl' > place.log 2>&1
