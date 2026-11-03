#!/bin/bash
set -euo pipefail
D=$(cd "$1" && pwd)
DK=docker; docker ps >/dev/null 2>&1 || DK='sudo docker'
$DK run --rm --name "codex-nf2-baseline-census-$$" --memory=4g --memory-swap=4g --cpus=1 \
 -v "$D/baseline":/baseline:ro -v "$D/kit":/work -v "$D/native_census.tcl":/native_census.tcl:ro \
 -e NF2_DB=/baseline/nf2_G_1_synth.odb -e NF2_OUT=/work/nf2_baseline_ff.tsv \
 openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -exit /native_census.tcl' > "$D/nf2_baseline_census.log" 2>&1
