#!/bin/bash
set -eu
docker run --rm -v /srv/opentallas-scratch/claude/closure-loop/hv15_vm_cal_x-xcap0030-cce3264d2/routes/hv15_vm_cal_x_xcap0030_cce3264d2/work/orfs:/work:ro -v /srv/opentallas-scratch/codex/calendar_raw_recovery_0253:/out -v /srv/opentallas-scratch/codex/calendar_raw_recovery_0253/macro:/mv0:ro openroad/orfs:latest /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -threads 1 -exit /out/raw.tcl > /srv/opentallas-scratch/codex/calendar_raw_recovery_0253/raw_export.log 2>&1
sha256sum /srv/opentallas-scratch/codex/calendar_raw_recovery_0253/raw.lef
