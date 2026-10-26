#!/bin/bash
set -eu
docker run --rm -v /srv/opentallas-scratch2/claude/closure-loop/hbm_su_static_bank6_clock7_1015-r12-0a5f7732e/routes/hbm_su_static_bank6_clock7_1015_r12_0a5f7732e/work/orfs:/work:ro -v /srv/opentallas-scratch/codex/su_raw_recovery_0310:/out -v /srv/opentallas-scratch/codex/su_raw_recovery_0310/macro:/mv0:ro openroad/orfs:latest /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -threads 1 -exit /out/raw.tcl > /srv/opentallas-scratch/codex/su_raw_recovery_0310/raw_export.log 2>&1
sha256sum /srv/opentallas-scratch/codex/su_raw_recovery_0310/raw.lef
