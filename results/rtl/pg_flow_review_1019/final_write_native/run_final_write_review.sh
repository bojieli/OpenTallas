#!/bin/bash
docker run --rm --entrypoint /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -v /srv/opentallas-scratch/claude/pg-native-hooks-1019:/clone:ro -v "$PWD":/proof sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29 -exit /proof/final_write_review.tcl > final_write_review.log 2>&1
rc=$?
cat final_write_review.log
exit "$rc"
