#!/bin/bash
# Round 9b: as f9 with 4-bit kept compare groups (screen copy only).
J=$(dirname $0)/screens.sh; F=results/rtl/hbm_clock_loops_20261004/fence
FF='ctl=(^|\.)(protected_state|live_a|live_b|live_c|bad_q|held_dirty_q)(\[|$)'
$J ${RND:-f9} lc1_g4 --source $F/fence_live_screen_g4.sv --top ot_hbm_rf_visibility_fence_live --param ENABLE=1 --param LATE_CHECK=1 --period-ns 0.833 --focus "$FF" &
wait
