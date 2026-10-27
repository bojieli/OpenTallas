set -euo pipefail
export PATH=$HOME/.local/opentallas-tools/bin:$PATH
verilator --binary --timing -O1 -Wno-fatal --top-module tb_clock_provider --Mdir obj --build-jobs 4 provider.sv clock_cells.v tb_provider.sv > build.log 2>&1
obj/Vtb_clock_provider > positive.log 2>&1
set +e
obj/Vtb_clock_provider +MUT_BRANCH > mutant.log 2>&1
rc=$?
set -e
test "$rc" != 0
grep 'HEAD_CLOCK_PROVIDER branch mismatch' mutant.log
grep 'HEAD_CLOCK_PROVIDER PASS' positive.log
