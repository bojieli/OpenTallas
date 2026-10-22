#!/bin/bash
set -e
D=/srv/opentallas-scratch/claude/codex-critical-pg-1020
docker run --rm -v /srv:/srv:ro -v "$D:/audit:ro" openroad/orfs:asap7lock /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /audit/qfd_sys_face-20261019-223453_4_cts.tcl > "$D/qfd_sys_face-20261019-223453_4_cts.log" 2>&1
docker run --rm -v /srv:/srv:ro -v "$D:/audit:ro" openroad/orfs:asap7lock /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /audit/qfd_sys_face-20261019-223453_5_1_grt.tcl > "$D/qfd_sys_face-20261019-223453_5_1_grt.log" 2>&1
