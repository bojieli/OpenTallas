#!/bin/bash
# Round 3: issue (two-stage item count) and bulk copy (registered look-ahead slots, deferred full clear, ping-pong output queue).
J=$(dirname $0)/screens.sh
SM="--domain 1.2GHz-SM"
FB='ctl=(^|\.)(q_cnt|q_wp|q_rp|act|a_addr|a_left|full|alloc_p|cons_p|oq_n|rd_v|head_full|next_full|space_q|outstanding|next_slot|next2_slot|take_q|clr_slot|oq_wp|oq_rp)(\[|$)'
BSRC="--source rtl/gpu/ot_gpu_bulk_copy.sv --source rtl/hbm_accel/epilogue/ot_hbm_accel_bulk_copy.sv --source physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2_bb.v"
B1K="--blackbox ot_sram_1r1w_1024x256_m2_r2c2 --macro ot_sram_1r1w_1024x256_m2_r2c2"
RND=r3 $(dirname $0)/r2.sh &
NEED=16 $J r3 bulk_q_e1 $BSRC --top ot_hbm_accel_bulk_copy --param ENABLE=1 --param LINE_BITS=1024 --param DEPTH=1024 --param MAX_OUT=512 --param SRAM_RING=1 $B1K --period-ns 0.833 $SM --focus "$FB" &
NEED=16 $J r3 bulk_ds_e1 $BSRC --top ot_hbm_accel_bulk_copy --param ENABLE=1 --param LINE_BITS=1088 --param DEPTH=1024 --param MAX_OUT=512 --param SRAM_RING=1 $B1K --period-ns 0.833 $SM --focus "$FB" &
wait
