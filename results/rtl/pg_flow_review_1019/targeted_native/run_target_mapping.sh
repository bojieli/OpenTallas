#!/bin/bash
docker run --rm --entrypoint /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -v /srv/opentallas-scratch/claude/pg-native-hooks-1019:/clone:ro -v "$PWD/source":/source:ro -v "$PWD":/proof sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29 -exit /proof/targeted_mapping.tcl > targeted_mapping.log 2>&1
rc=$?
cat targeted_mapping.log
exit "$rc"
