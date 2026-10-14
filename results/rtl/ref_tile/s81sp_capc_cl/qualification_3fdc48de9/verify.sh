#!/bin/bash
set -u
bash tools/s81_ph/capc_bench.sh bench exact "mix mix11 err over range" > exact.out 2>&1
pos=$?
bash tools/s81_ph/capc_bench.sh benchm mut "mix" S81PH_CAPC_MUT_KSWAP > mut.out 2>&1
mut=$?
printf 'positive_rc=%s\nmutant_rc=%s\n' "$pos" "$mut" > checks.rc
cat checks.rc
[ "$pos" = 0 ] && [ "$mut" = 1 ] && grep -q '^CAPC_EQ mismatches=[1-9]' benchm/run_mut_mix.log
