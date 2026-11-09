#!/bin/bash
# DIE-S81-85 11-09 dchn_kr bench: ref = main RX (RXB vC defines), new = OT_S81_RCK_RXB_CHNKR (dchn_kr + ddly DD+1), SHIFT 1.
set -uo pipefail
H=$(cd "$(dirname "$0")"; pwd); E=$H/out; mkdir -p $E
export PATH=/home/ubuntu/.local/opentallas-tools/bin:$PATH
C=$H/common
BASE="-DOT_S81_RCK_REFORM -DOT_S81_RCK_RELAY4 -DOT_S81_KP4_AM_FACE3 -DOT_S81_KP4_SYN_LOCAL -DOT_S81_KP4_BM_PE_LOCAL -DOT_S81_LPL_CHUNK -DOT_S81_RCK_RXB_FACE_RET -DOT_S81_RCK_RXS_THC -DOT_S81_RCK_RX_SPCYC -DOT_S81_RCK_RXB_DQREG"
UNCH="$C/ot_s81_kp4_common.sv $C/ot_s81_kp4_dout.sv $C/ot_s81_kp4_dchn.sv $C/ot_s81_kp4_bm.sv $C/ot_s81_kp4_enc.sv $C/ot_s81_kp4_dsyn.sv $C/ot_pl_land.sv $C/sram_stubs.sv"
ren(){ local f=$1 sfx=$2; for m in $(grep -oP '^\s*module\s+\K\w+' $f | sort -u); do sed -i -E "s/\b$m\b/${m}${sfx}/g" $f; done; }
run(){ local n=$1 sh=$2; shift 2; local D=$E/$n; mkdir -p $D
  verilator -E -P -I$C $BASE $UNCH $H/ref/ot_s81_kp4_ddly.sv $H/ref/ot_s81_rck_reform.sv > $D/ref.sv 2>$D/pp_r.log || { echo "$n PP_FAIL"; return; }; ren $D/ref.sv _r
  verilator -E -P -I$C $BASE "$@" $UNCH $H/new/ot_s81_kp4_dchn_kr.sv $H/new/ot_s81_kp4_ddly.sv $H/new/ot_s81_rck_reform.sv > $D/new.sv 2>$D/pp_n.log || { echo "$n PP_FAIL"; return; }; ren $D/new.sv _n
  nice verilator --binary --timing -j 8 -O1 -Wno-fatal -Wno-WIDTH -Wno-MULTIDRIVEN -Wno-UNOPTFLAT -DSHIFT=$sh --x-initial unique --x-assign unique \
     --top-module tb --Mdir $D/obj -o tb $C/tb_rx.sv $D/ref.sv $D/new.sv > $D/build.log 2>&1 || { echo "$n BUILD_FAIL $(grep -m3 -i error $D/build.log)"; return; }
  for seed in ${SEEDS:-1}; do $D/obj/tb +verilator+rand+reset+${RR:-0} +verilator+seed+$seed > $D/run_s$seed.log 2>&1; echo "$n seed=$seed rc=$? $(grep -hE '_RESULT|PASS|FAILED' $D/run_s$seed.log | tr '\n' ' ')"; done; }
: > $E/summary.log
{
SEEDS="1 2 3" run chnkr      1 -DOT_S81_RCK_RXB_CHNKR
SEEDS="1"     run chnkr_mut  1 -DOT_S81_RCK_RXB_CHNKR -DRCKRF_MUT_CHNKR
SEEDS="1"     run chnkr_sh0  0 -DOT_S81_RCK_RXB_CHNKR
SEEDS="1"     run default    0
} 2>&1 | tee -a $E/summary.log
