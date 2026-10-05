#!/bin/bash
# Round 5+: LATE_CHECK=1 with the in-cycle dirty gate + registered exact decode + flat select.
J=$(dirname $0)/screens.sh; F=results/rtl/hbm_clock_loops_20261004/fence
FF='ctl=(^|\.)(protected_state|live_a|live_b|live_c|bad_q|held_dirty_q)(\[|$)'
$J ${RND:-f5} live_lc1 --source $F/fence_live_screen.sv --top ot_hbm_rf_visibility_fence_live --param ENABLE=1 --param LATE_CHECK=1 --period-ns 0.833 --focus "$FF" &
wait
