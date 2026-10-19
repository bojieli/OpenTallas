#!/bin/bash
# MU-DQ-TOK 10-19: paired compute<->KV D2D co-sim on the NETLISTED seams of the MU release dies.
# compute dv2f18mu (record_bundle_audit PASS 9: C.tx_slot 2, C.rx_record 2, lnk_kv_x3_slot E2 -> 3, C.tx_record 2, C.x3_record 2)
# KV kvs14r-bce531645-mu (BUNDLE_EQ K.rx_record 11, K.tx_slot 9, K.tx_record 9; die NTX 3, die TXDP 0x03030418 = d2ds FRAME stand-in)
# GEN-bound TXDP: compute 0x09010308 (C 8,3,1,9), KV 0x03030418 (K 24,4,3,3).  Compiled for this seam: C 8,3,1,10 / K 21,4,3,3.
set -u
W=/srv/opentallas-scratch/claude/mu-dq-tok/xdie; cd $W/src
export XQ_PLAN=2,2,2,3,2,2/11,11,9,9,9,9,9 XQ_G=-GK_NTX=3 XQ_TXDP_OFF1=9,3,1,10/21,4,3,3 JOBS=4
( XQ_GEN_TXDP=8,3,1,9/24,4,3,3 XQ_GEN_TXDP_EXPECT=FAIL bash rtl/test/qwen_split/run_xdie_exchange.sh $W/pair_mu \
   pair pair_t8192 pair_phy9 pair_l0 pair_l0_phy9 pair_gen_txdp pair_mut_txdp_c_off1 pair_mut_kseam_rx_torn \
   pair_mut_kseam_tx_torn pair_mut_status_done pair_mut_result_bit pair_mut_phy_bit > $W/pair_mu.out 2>&1 ) &
( XQ_GEN_TXDP=8,3,1,9/21,4,3,3 XQ_GEN_TXDP_EXPECT=FAIL bash rtl/test/qwen_split/run_xdie_exchange.sh $W/gen_c_only pair_gen_txdp > $W/gen_c_only.out 2>&1 ) &
( XQ_GEN_TXDP=8,3,1,10/24,4,3,3 XQ_GEN_TXDP_EXPECT=FAIL bash rtl/test/qwen_split/run_xdie_exchange.sh $W/gen_k_only pair_gen_txdp > $W/gen_k_only.out 2>&1 ) &
wait
grep -h -E 'expect=' $W/pair_mu.out $W/gen_c_only.out $W/gen_k_only.out
echo XDIE_MU_DONE
