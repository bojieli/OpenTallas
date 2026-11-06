#!/bin/bash
set -eu
cd "$(dirname "$0")"
docker run --rm --memory=4g --cpus=1 -v "$PWD":/proof -w /proof openroad/orfs:asap7lock bash -lc "yosys -l eq_lower.log eq_lower.ys > eq_lower.stdout 2>&1"
echo COLLECTOR_FORMAL24_PASS
