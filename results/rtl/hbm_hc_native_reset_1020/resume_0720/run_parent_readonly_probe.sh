#!/bin/bash
set -euo pipefail
iverilog-vpi parent_readonly_probe.c > probe_build.log 2>&1
set +e
vvp -M. -mparent_readonly_probe parent.vvp +MUT=0 +REQUEST_PHASE=9 > parent_phase9_readonly_probe.log
rc=$?
set -e
echo "ORIGINAL_PHASE9_EXPECTED_POSITIVE_RC=$rc"
grep 'PARENT_READONLY\|WATCHDOG' parent_phase9_readonly_probe.log
