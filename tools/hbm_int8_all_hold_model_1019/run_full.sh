#!/bin/bash
set -euo pipefail
base=/srv/opentallas-scratch/claude/hbm-int8-cts-v2-run-1019
own=/srv/opentallas-scratch/claude/hbm-int8-all-hold-model-1019
sha256sum -c "$base/output/checkpoint.sha256"
for corner in FF TT; do
 docker run --rm --user "$(id -u):$(id -g)" -e INT8_CORNER="$corner" -v "$base:/work:ro" -v "$own:/audit" sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29 /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /audit/census_full.tcl > "$own/census_${corner}.log" 2>&1
 gzip -k "$own/"${corner}_*.json
done
sha256sum -c "$base/output/checkpoint.sha256"
