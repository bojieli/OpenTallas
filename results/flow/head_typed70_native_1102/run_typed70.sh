#!/bin/bash
set -uo pipefail
R=/srv/opentallas-scratch2/claude/codex-head-typed70-0248
DK=docker; docker ps >/dev/null 2>&1 || DK="sudo docker"
$DK run --rm --cpus=2 --memory=8g --memory-swap=8g -v "$R:/out" -w /out sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29 bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; python3 -u /out/head_typed70_native.py'
