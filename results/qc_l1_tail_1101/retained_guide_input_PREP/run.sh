#!/bin/bash
set -euo pipefail
exec docker run --rm --cpus 2 --memory 8g --memory-swap 8g -v /srv/opentallas-scratch2/claude/codex-qc-l1-retained-guard-api-1102:/input:ro -v "$PWD":/prep -w /prep openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -exit /prep/prepare.tcl > /prep/prepare.log 2>&1; openroad -python -exit /prep/check_input.py > /prep/compare.log 2>&1'
