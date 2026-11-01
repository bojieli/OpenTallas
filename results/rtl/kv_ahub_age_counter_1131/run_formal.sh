#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
DK=docker; $DK ps >/dev/null 2>&1 || DK='sudo docker'
$DK run --rm --memory=1g --memory-swap=1g --cpus=1 -v "$PWD":/work -w /work openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; yosys -V > formal_tool.txt; yosys -ql normal.log normal.ys || exit $?; yosys -ql mutant.log mutant.ys; rc=$?; test $rc != 0 || exit 1; grep -q "proof did fail" mutant.log || exit 1; chown -R '"$(id -u):$(id -g)"' /work'
echo 'AHUB_AGE_COUNTER_INDUCTION PASS all16-bitages/active/reset/start/MUT4; wrongstart+1 mutant CAUGHT'
