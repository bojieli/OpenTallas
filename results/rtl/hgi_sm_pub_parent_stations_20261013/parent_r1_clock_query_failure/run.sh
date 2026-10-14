#!/bin/bash
set -eu
R=/srv/opentallas-scratch2/claude/closure-loop/smpub_parent-r1-490ae2be6
W=$R/routes/smpub_parent_r1_490ae2be6.attempt1/work/orfs
docker run --rm -v "$R/src:/src:ro" -v "$W:/work:ro" -v /tmp:/probe -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; python3 /src/tools/orfs_hold_mm.py /OpenROAD-flow-scripts/flow/scripts >/dev/null; make NUM_CORES=4 DESIGN_CONFIG=/work/config.mk WORK_HOME=/work FLOW_VARIANT=base LOG_DIR=/probe/smpub-rsz-probe-logs REPORTS_DIR=/probe/smpub-rsz-probe-reports OBJECTS_DIR=/probe/smpub-rsz-probe-objects RUN_SCRIPT=/probe/smpub-rsz-debug-probe.tcl RUN_LOG_NAME_STEM=debug run' > /tmp/smpub-rsz-debug-output.log 2>&1
