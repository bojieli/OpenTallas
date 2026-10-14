#!/bin/bash
set -u
export PATH="$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH"
bash tools/s81_ph/capc_bench.sh bench exact 'mix mix11 mix12 mix13 trace err over range rreq'
exact_rc=$?
bash tools/s81_ph/capc_bench.sh bench mutant mix S81PH_CAPC_MUT_KSWAP
mutant_rc=$?
echo "COUNTER_BENCH exact_rc=$exact_rc mutant_rc=$mutant_rc"
test "$exact_rc" = 0 && test "$mutant_rc" = 1
