#!/bin/bash
# Round 7: dirty only in the write enable and release outputs (select sees flop flags); kept syndrome/diff groups.
J=$(dirname $0)/screens.sh; F=results/rtl/hbm_clock_loops_20261004/fence
FF='ctl=(^|\.)(protected_state|live_a|live_b|live_c|bad_q|held_dirty_q)(\[|$)'
$J ${RND:-f7} lc1_keep --source $F/fence_live_screen.sv --top ot_hbm_rf_visibility_fence_live --param ENABLE=1 --param LATE_CHECK=1 --period-ns 0.833 --focus "$FF" &
wait
