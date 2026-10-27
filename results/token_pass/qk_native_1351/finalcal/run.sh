#!/bin/bash
set -euo pipefail
export PATH="$HOME/.local/opentallas-tools/bin:$PATH"
verilator --binary --timing -Wno-fatal --top-module tb_finalcal -j 1 tb_finalcal.sv > build.log 2>&1
./obj_dir/Vtb_finalcal +POST=0 +LATE=0 > post0.log 2>&1
echo $? > post0.exit
set +e
./obj_dir/Vtb_finalcal +POST=5 +LATE=1 > late_fault.log 2>&1
rc=$?
echo "$rc" > late_fault.exit
set -e
[ "$rc" != 0 ]
grep "KVSLICE_FINALCAL dcal_fault 1" late_fault.log
cat post0.log
