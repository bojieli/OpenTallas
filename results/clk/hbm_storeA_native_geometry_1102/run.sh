#!/bin/bash
set -euo pipefail
KIT=/srv/opentallas-scratch2/claude/codex-storeA-native-sourceproof-0048/kits/ot_hnx_sfu_store_a__da81d76763c9_4b48edda3499-source_eq
ODB=$KIT/run/results/asap7/hbc_ot_hnx_sfu_store_a__da81d76763c9/base/1_synth.odb
sha256sum "$ODB" > source_odb.sha256
cp "$KIT/freeze.json" freeze.json
cp "$KIT/macro_placement.tcl" macro_placement.tcl
/usr/bin/time -v docker run --rm --name codex-storeA-native-census-0455 --memory=4g --memory-swap=4g --cpus=1 -v /srv/opentallas-scratch2:/srv/opentallas-scratch2:ro -v "$PWD:/out" -e "INPUT_ODB=$ODB" openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -no_init -threads 1 -exit /out/dump.tcl' > dump.log 2>&1
python3 -u analyze.py
