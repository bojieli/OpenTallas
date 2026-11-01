#!/bin/bash
set -uo pipefail
R=${1:-$PWD}
cd "$R"
docker run --rm --cpus 2 --memory 4g --memory-swap 4g -v "$R":/work -w /work verilator/verilator:v5.032 --binary --timing -Wno-fatal --top-module tb -j 2 --Mdir obj_good old.sv new.sv stubs.sv tb.sv > good_build.log 2>&1 || exit $?
./obj_good/Vtb > good.log 2>&1 || exit $?
docker run --rm --cpus 2 --memory 4g --memory-swap 4g -v "$R":/work -w /work verilator/verilator:v5.032 --binary --timing -Wno-fatal --top-module tb -j 2 --Mdir obj_mut old.sv mut.sv stubs.sv tb.sv > mutant_build.log 2>&1 || exit $?
set +e
./obj_mut/Vtb > mutant.log 2>&1
RC=$?
set -e
[ "$RC" != 0 ] && grep -q SX_ALIAS_MISMATCH mutant.log || exit 3
printf 'SX_ALIAS_MUTANT CAUGHT rc%s\n' "$RC"
docker run --rm --cpus 2 --memory 2g --memory-swap 2g -v "$R":/work -w /work openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; yosys -Q -T -p "read_verilog -sv -noautowire new.sv stubs.sv; hierarchy -check -top sx_new; proc; check"' > yosys.log 2>&1
