#!/bin/bash
set -euo pipefail
R=/srv/opentallas-scratch2/claude/codex-cap-west2-0730-r1
for MODE in copy audit; do
 docker run --rm --network none --memory=8g --memory-swap=8g --cpus=1 -v "$R":/out -e MODE="$MODE" sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29 /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -python -threads 1 -exit /out/west2_native.py > "$R/$MODE.log" 2>&1
done
