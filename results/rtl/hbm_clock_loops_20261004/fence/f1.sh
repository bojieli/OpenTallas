#!/bin/bash
J=$(dirname $0)/screens.sh; F=results/rtl/hbm_clock_loops_20261004/fence
FF='ctl=(^|\.)(protected_state|live_a|live_b|live_c|bad_q)(\[|$)'
$J ${RND:-f1} w6_base --source $F/fence_w6_screen.sv --top ot_gpu_rf_visibility_fence_w6 --param ENABLE=1 --period-ns 0.833 --focus "$FF" &
$J ${RND:-f1} live_lc0 --source $F/fence_live_screen.sv --top ot_hbm_rf_visibility_fence_live --param ENABLE=1 --param LATE_CHECK=0 --period-ns 0.833 --focus "$FF" &
$J ${RND:-f1} live_lc1 --source $F/fence_live_screen.sv --top ot_hbm_rf_visibility_fence_live --param ENABLE=1 --param LATE_CHECK=1 --period-ns 0.833 --focus "$FF" &
wait
