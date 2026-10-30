#!/bin/bash
set -e
R=/srv/opentallas-scratch2/claude/codex-head-lep-serdes-2249
bash "$R/serdes_rstwest/run_kit_hbm.sh" "$R/serdes_rstwest" route 48 8 > "$R/serdes_rstwest/run_route.log" 2>&1
