#!/bin/bash
set -eu
O=${1:?output};mkdir -p "$O"
export VERILATOR=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
export GUNIT_DEFS='-DOT_S81_VE_LOADSAFE5 -DOT_S81_GUNIT_FWDOWN'
bash rtl/dsrom_sys/s81_dv/unit/test/run_gunit_bench.sh "$O/positive" 8 0 > "$O/positive.log" 2>&1
cat "$O/positive.log"
set +e
bash rtl/dsrom_sys/s81_dv/unit/test/run_gunit_bench.sh "$O/mutant" 4 1 > "$O/mutant.log" 2>&1
rc=$?
set -e
[ "$rc" -ne 0 ] && grep -q 'MUT=1: GUNIT FAIL ' "$O/mutant.log"
echo GUNIT_FORWARD_OWNER_CAUSAL_MUTANT_CAUGHT
