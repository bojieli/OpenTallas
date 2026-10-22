#!/bin/bash
docker run --rm --entrypoint /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -v /srv/opentallas-scratch/claude/pg-native-hooks-1019:/clone:ro -v /srv/opentallas-scratch/claude/pg-native-admission-integration-1019:/proof sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29 -exit /proof/pin_pattern_probe_v3.tcl > pin_pattern_probe_v3.log 2>&1
rc=$?
cat pin_pattern_probe_v3.log
exit "$rc"
