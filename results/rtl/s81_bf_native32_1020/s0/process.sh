#!/bin/bash
set -eu
docker image inspect --format '{{.Id}}' openroad/orfs:latest > image_id.txt
docker run --rm -v "$PWD/src:/src:ro" -v "$PWD/tools:/tools:ro" -v "$PWD/work:/work" -v "$PWD/admission:/admission:ro" -v "$PWD/process.py:/process.py:ro" -w /OpenROAD-flow-scripts/flow openroad/orfs:latest bash -lc 'trap "chmod -R a+rwX /work >/dev/null 2>&1 || true" EXIT; source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; yosys -V > /work/yosys_version.txt; python3 /process.py'
