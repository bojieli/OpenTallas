#!/bin/bash
set -eu
cd src
cp ../native_*.mk ../native.sdc .
kind=$1
docker run --rm -v "$PWD:/work" -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; make -B DESIGN_CONFIG=/work/native_'"$kind"'.mk WORK_HOME=/work/native_orfs_'"$kind"'_wc4 synth' > ../native_synth_${kind}_wc4.log 2>&1
