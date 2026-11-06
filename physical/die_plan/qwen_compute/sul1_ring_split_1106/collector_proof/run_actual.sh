#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
docker run --rm --memory=4g --cpus=1 -v $PWD:/proof -w /proof openroad/orfs:asap7lock bash -lc "yosys -l good.log good.ys >good.stdout 2>&1"
set +e
docker run --rm --memory=4g --cpus=1 -v $PWD:/proof -w /proof openroad/orfs:asap7lock bash -lc "yosys -l mutant.log mutant.ys >mutant.stdout 2>&1"
rc=$?
set -e
[ $rc -ne 0 ] || exit 4
grep -q "proof did fail" mutant.log
echo ACTUAL_SU2_COLLECTOR_SAT32_PASS_MUTANT_CAUGHT
