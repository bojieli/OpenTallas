#!/bin/bash
# Round 1: baselines (original ot_gpu_*) vs HA3 look-ahead successors (ENABLE=1), 0.833 ns SS 60 ps.
J=$(dirname $0)/screens.sh
SM="--domain 1.2GHz-SM"
FI='issue=(^|\.)(ph|si|rb|gi|ti|issuing|retired|cr|cg|cxb|wb|items_q|rows_q|xa_r|valid_mask|next_mask|c_end|g_end|slot_glast|init_q|busy)(\[|$)'
FB='ctl=(^|\.)(q_cnt|q_wp|q_rp|act|a_addr|a_left|full|alloc_p|cons_p|oq_n|rd_v|head_full|next_full|space_q|outstanding)(\[|$)'
ISRC="--source rtl/gpu/ot_gpu_issue.sv --source rtl/hbm_accel/epilogue/ot_hbm_accel_issue.sv"
BSRC="--source rtl/gpu/ot_gpu_bulk_copy.sv --source rtl/hbm_accel/epilogue/ot_hbm_accel_bulk_copy.sv --source physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2_bb.v"
B1K="--blackbox ot_sram_1r1w_1024x256_m2_r2c2 --macro ot_sram_1r1w_1024x256_m2_r2c2"
for e in 0 1; do
 $J r1 issue_q_e$e $ISRC --top ot_hbm_accel_issue --param ENABLE=$e --param IL=8 --param RMAX=4096 --param XDEPTH=1024 --period-ns 0.833 $SM --focus "$FI" &
 $J r1 issue_ds_e$e $ISRC --top ot_hbm_accel_issue --param ENABLE=$e --param IL=8 --param RMAX=4096 --param XDEPTH=128 --period-ns 0.833 $SM --focus "$FI" &
 NEED=16 $J r1 bulk_q_e$e $BSRC --top ot_hbm_accel_bulk_copy --param ENABLE=$e --param LINE_BITS=1024 --param DEPTH=1024 --param MAX_OUT=512 --param SRAM_RING=1 $B1K --period-ns 0.833 $SM --focus "$FB" &
 NEED=16 $J r1 bulk_ds_e$e $BSRC --top ot_hbm_accel_bulk_copy --param ENABLE=$e --param LINE_BITS=1088 --param DEPTH=1024 --param MAX_OUT=512 --param SRAM_RING=1 $B1K --period-ns 0.833 $SM --focus "$FB" &
done
wait
