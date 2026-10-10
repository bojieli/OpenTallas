#!/bin/bash
# run in src root: rbench.sh <outroot>
O=$1; rm -rf $O; mkdir -p $O
P=rtl/hbm_accel/tu/link_retry_pipeline_20261009; D=rtl/hbm_accel/tu/link_retry_sram_20261008
S="rtl/common/ot_secded.sv physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v rtl/common/ot_secded_dec_dp.sv $D/ot_hbm_replay_sram_dp.sv $P/ot_hbm_link_retry_pipeline_cl.sv $P/tb_hbm_link_retry_pipeline.sv"
B="-DOT_HBM_RETRY_NO_REG_POISON -DOT_RETRY_RSTR"
FULL="$B -DOT_RETRY_RX_SLOT_SAMPLE -DOT_RETRY_TX_SLOT_SAMPLE -DOT_RETRY_IN_PIN"
run(){ n=$1; exp=$2; shift 2; ( iverilog -g2012 -Irtl/common -s tb_hbm_link_retry_pipeline "$@" -o $O/$n $S > $O/$n.build 2>&1 && vvp -n $O/$n > $O/$n.log 2>&1; rc=$?; r=FAIL; grep -q PASS_ALL $O/$n.log && [ $rc = 0 ] && r=PASS; echo "$n expect=$exp got=$r $(grep -m1 -i fatal $O/$n.log | cut -c1-100)" ) & }
run base_rstr PASS $B
run rxslot PASS $B -DOT_RETRY_RX_SLOT_SAMPLE
run full PASS $FULL
run full_noRX PASS $B -DOT_RETRY_TX_SLOT_SAMPLE -DOT_RETRY_IN_PIN
run m_dup FAIL $FULL -DOT_HBM_RETRY_PIPE_MUT_DUPLICATE
run m_txhold FAIL $FULL -DOT_RETRY_MUT_TX_SLOT_HOLD
run m_inpinhold FAIL $FULL -DOT_RETRY_MUT_IN_PIN_HOLD
run m_nogate FAIL $FULL -DOT_RETRY_MUT_RSTR_NOGATE
wait
