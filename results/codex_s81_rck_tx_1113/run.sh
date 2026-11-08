#!/bin/bash
# S81-TYPES-9-RCK 11-08 bench: run.sh <worktree> <outdir>
# reference = old/ (the RTL of claude/s81-types-7-rck-1108@872819503b, the current RCK cores); new = the worktree RTL.
set -uo pipefail
W=$1; E=$2; H=$(cd "$(dirname "$0")"; pwd); mkdir -p "$E"
export PATH=/home/ubuntu/.local/opentallas-tools/bin:$PATH
S=$W/rtl/dsrom_sys/s81_link; L=$W/rtl/common/landed_parent/ot_pl_land.sv
BASE="-DOT_S81_RCK_REFORM -DOT_S81_RCK_RELAY4 -DOT_S81_KP4_AM_FACE3 -DOT_S81_KP4_SYN_LOCAL -DOT_S81_KP4_BM_PE_LOCAL -DOT_S81_LPL_CHUNK -DOT_S81_RCK_RXB_FACE_RET"
UNCH="$S/ot_s81_kp4_common.sv $S/ot_s81_kp4_bm.sv $S/ot_s81_kp4_dout.sv $S/ot_s81_kp4_dchn.sv $L $H/sram_stubs.sv"
OLDF="$H/old/ot_s81_kp4_enc.sv $H/old/ot_s81_kp4_dsyn.sv $H/old/ot_s81_kp4_ddly.sv $H/old/ot_s81_rck_reform.sv"
NEWF="$S/ot_s81_kp4_enc.sv $S/ot_s81_kp4_dsyn.sv $S/ot_s81_kp4_ddly.sv $S/col/ot_s81_rck_reform.sv"
ren(){ local f=$1 sfx=$2; for m in $(grep -oP '^\s*module\s+\K\w+' $f | sort -u); do sed -i -E "s/\b$m\b/${m}${sfx}/g" $f; done; }
# case <name> <tb> <shift> <new defines...>
run(){ local n=$1 tb=$2 sh=$3; shift 3; local D=$E/$n; mkdir -p $D
  verilator -E -P -I$S $BASE $UNCH $OLDF > $D/ref.sv 2>$D/pp_r.log || { echo "$n PP_FAIL"; return; }; ren $D/ref.sv _r
  verilator -E -P -I$S $BASE "$@" $UNCH $NEWF > $D/new.sv 2>$D/pp_n.log || { echo "$n PP_FAIL"; return; }; ren $D/new.sv _n
  nice verilator --binary --timing -j 6 -O1 -Wno-fatal -Wno-WIDTH -Wno-MULTIDRIVEN -Wno-UNOPTFLAT -DSHIFT=$sh --x-initial unique --x-assign unique \
     --top-module tb --Mdir $D/obj -o tb $H/$tb $D/ref.sv $D/new.sv > $D/build.log 2>&1 || { echo "$n BUILD_FAIL $(grep -m3 -i error $D/build.log)"; return; }
  for seed in ${SEEDS:-1}; do $D/obj/tb +verilator+rand+reset+2 +verilator+seed+$seed > $D/run_s$seed.log 2>&1; echo "$n seed=$seed rc=$? $(grep -hE '_RESULT|PASS|FAILED' $D/run_s$seed.log | tr '\n' ' ')"; done; }
: > $E/summary.log
{
SEEDS="1 2 3" run tx_vG        tb_tx.sv 1 -DOT_S81_RCK_TX_PPCYC
SEEDS="1"     run tx_mut_ppcyc tb_tx.sv 1 -DOT_S81_RCK_TX_PPCYC -DRCKRF_MUT_PPCYC
SEEDS="1 2"   run rx_full      tb_rx.sv 1 -DOT_S81_RCK_RXS_THC -DOT_S81_RCK_RX_SPCYC -DOT_S81_RCK_RXB_DQREG
SEEDS="1"     run rx_default   tb_rx.sv 0
SEEDS="1"     run rx_dqreg     tb_rx.sv 0 -DOT_S81_RCK_RXB_DQREG
SEEDS="1"     run rx_thc       tb_rx.sv 0 -DOT_S81_RCK_RXS_THC
SEEDS="1"     run rx_mut_spcyc tb_rx.sv 1 -DOT_S81_RCK_RXS_THC -DOT_S81_RCK_RX_SPCYC -DOT_S81_RCK_RXB_DQREG -DRCKRF_MUT_SPCYC
SEEDS="1"     run rx_mut_ddsp  tb_rx.sv 1 -DOT_S81_RCK_RXS_THC -DOT_S81_RCK_RX_SPCYC -DOT_S81_RCK_RXB_DQREG -DRCKRF_MUT_DDSP
SEEDS="1"     run rx_mut_dqreg tb_rx.sv 1 -DOT_S81_RCK_RXS_THC -DOT_S81_RCK_RX_SPCYC -DOT_S81_RCK_RXB_DQREG -DRCKRF_MUT_DQREG
} 2>&1 | tee -a $E/summary.log
