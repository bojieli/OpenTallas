#!/bin/bash
set -euo pipefail
R=/srv/opentallas-scratch2/claude/codex-head-ptake45-1010
cd "$R"
test "$(sha256sum ptake45.py | cut -d' ' -f1)" = 6ba7a233b8f2a40f9019ded768d29220e465fe2e7856212258774fbab9c324df
docker run --rm --cpus=2 --memory=8g --memory-swap=8g -v "$R":/out -v "$R/subject":/out/subject:ro -v "$R/TYPED70_CERTIFICATE.json":/out/TYPED70_CERTIFICATE.json:ro -w /out sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29 bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; python3 -u /out/ptake45.py'
