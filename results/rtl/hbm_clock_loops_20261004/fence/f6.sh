#!/bin/bash
# Round 6: factored decision (no compare through invalid_input), linear delta encodes; kept vs free compare groups.
J=$(dirname $0)/screens.sh; F=results/rtl/hbm_clock_loops_20261004/fence
FF='ctl=(^|\.)(protected_state|live_a|live_b|live_c|bad_q|held_dirty_q)(\[|$)'
$J ${RND:-f6} lc1_keep --source $F/fence_live_screen.sv --top ot_hbm_rf_visibility_fence_live --param ENABLE=1 --param LATE_CHECK=1 --period-ns 0.833 --focus "$FF" &
$J ${RND:-f6} lc1_nokeep --source $F/fence_live_screen_nokeep.sv --top ot_hbm_rf_visibility_fence_live --param ENABLE=1 --param LATE_CHECK=1 --period-ns 0.833 --focus "$FF" &
wait
