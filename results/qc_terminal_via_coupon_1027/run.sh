#!/bin/bash
set -eu
docker run --rm --memory 8g --memory-swap 8g -v /srv/opentallas-scratch2/claude/codex-qc-via-coupon2-1027:/w openroad/orfs:latest bash -lc "set -eu; source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; for case in down_m5 up_m9; do openroad -no_init -exit /w/\$case.tcl > /w/\$case.log 2>&1; grep -q VIA_COUPON_DONE /w/\$case.log; done; openroad -no_init -python -exit /w/check.py > /w/check.log 2>&1"
