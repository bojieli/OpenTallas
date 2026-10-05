#!/bin/bash
# Round 2: retimed issue look-ahead (pre-incremented cursors, registered turn/chunk/wave/retire flags).
J=$(dirname $0)/screens.sh
SM="--domain 1.2GHz-SM"
FI='issue=(^|\.)(ph|si|rb|gi|ti|issuing|rem|cr|cg|cxb|wb|items_q|rows_q|xa_r|valid_mask|next_mask|c_end|g_end|slot_glast|init_q|busy|turn_q|lt_q|lw_q|.*_n)(\[|$)'
ISRC="--source rtl/gpu/ot_gpu_issue.sv --source rtl/hbm_accel/epilogue/ot_hbm_accel_issue.sv"
$J ${RND:-r2} issue_q_e1 $ISRC --top ot_hbm_accel_issue --param ENABLE=1 --param IL=8 --param RMAX=4096 --param XDEPTH=1024 --period-ns 0.833 $SM --focus "$FI" &
$J ${RND:-r2} issue_ds_e1 $ISRC --top ot_hbm_accel_issue --param ENABLE=1 --param IL=8 --param RMAX=4096 --param XDEPTH=128 --period-ns 0.833 $SM --focus "$FI" &
wait
