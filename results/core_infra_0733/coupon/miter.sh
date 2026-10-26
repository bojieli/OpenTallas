#!/bin/bash
set -euo pipefail
TASK_DIR=$(cd "$(dirname "$0")" && pwd)
cd "$TASK_DIR"
YOSYS=$HOME/.local/opentallas-tools/bin/yosys
"$YOSYS" -Q -T -p 'read_verilog -formal -sv models.v coupon_final.v; prep -top miter -flatten; opt; chformal -lower; sat -seq 5 -set-init-zero -prove-asserts -verify' > miter_positive.log 2>&1
set +e
"$YOSYS" -Q -T -p 'read_verilog -DMUTANT -formal -sv models.v coupon_final.v; prep -top miter -flatten; opt; chformal -lower; sat -seq 5 -set-init-zero -prove-asserts -verify' > miter_mutant.log 2>&1
rc=$?
set -e
if [ "$rc" = 0 ]; then echo MUTANT_ESCAPED; exit 1; fi
grep -q 'proof did fail' miter_mutant.log
echo 'CORE_INFRA_LOCKSTEP_PASS MUTANT_CAUGHT DATA_CYCLES0 RESET_CYCLES0'
