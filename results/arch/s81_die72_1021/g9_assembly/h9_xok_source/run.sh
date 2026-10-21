#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
sha256sum input.odb read.tcl > before.sha256
docker run --rm --memory=14g -v "$PWD:/work:ro" openroad/orfs:latest bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -threads 2 -no_init -exit /work/read.tcl' > read.log 2>&1
sha256sum input.odb read.tcl > after.sha256
cmp before.sha256 after.sha256
cat read.log
