#!/bin/bash
set -eu
cd /srv/opentallas-scratch2/claude/codex-s81-rck-1106/relay4_native
SRCS='tb.sv hold.sv rate_match.sv lp_old.sv lp_new.sv syn_old.sv syn_new.sv ot_s81_kp4_common.sv ot_s81_kp4_bm.sv ot_s81_kp4_ddly.sv ot_s81_kp4_dchn.sv ot_s81_kp4_dout.sv ot_pl_land.sv ot_sram_1r1w2c_64x546_m1.v ot_sram_1r1w_32x546_m1.v'
for mutant in 0 5 6;do
 iverilog -g2012 -I. -DOT_S81_KP4_AM_FACE3 -DOT_S81_RCK_RELAY4 -s tb -Ptb.MUT=$mutant -o "mut$mutant.vvp" $SRCS > "mut$mutant.build.log" 2>&1
 if vvp "mut$mutant.vvp" > "mut$mutant.log" 2>&1;then
  [ "$mutant" = 0 ] || { echo "NATIVE_MUTANT_SURVIVED $mutant";exit 1; }
 else
  [ "$mutant" != 0 ] || { cat "mut$mutant.log";exit 1; }
 fi
 cat "mut$mutant.log"
done
