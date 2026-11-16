#!/bin/bash
# run_pdie_fanout_eq.sh <src root> <out dir> (FABLE-FIX-HEAD-SERDES 2026-11-16): cycle-exact gate of the fanout-copy form of
# ot_pdie_serdes (DNGB 12, RMRPC 32 = the hd_serdes link adapters) against the default form: tb_s81_pdie_fanout_eq.sv.
# base must PASS (differ=0), mutant RMRPC_MUT_STALE (one read-select copy stalls) must FAIL.  Prints PDIE_FANOUT_EQ PASS|FAIL.
set -u
SRC=$1; OUT=$2; mkdir -p $OUT
L=$SRC/rtl/dsrom_sys/s81_link; M=$SRC/physical/asap7_memory_macros
F="$L/ot_s81_kp4_common.sv $L/ot_s81_kp4_enc.sv $L/ot_s81_kp4_bm.sv $L/ot_s81_kp4_dsyn.sv $L/ot_s81_kp4_ddly.sv $L/ot_s81_kp4_dchn.sv $L/ot_s81_kp4_dout.sv $L/ot_s81_kp4_dec.sv $M/ot_sram_1r1w2c_64x546_m1/ot_sram_1r1w2c_64x546_m1.v $M/ot_sram_1r1w_32x546_m1/ot_sram_1r1w_32x546_m1.v $L/ot_pdie_serdes.sv $L/tb_s81_pdie_fanout_eq.sv"
run() { l=$1; shift
  verilator --binary --timing -j 16 -Wno-fatal -Wno-WIDTH -Wno-lint -Wno-style -Wno-UNOPTFLAT +incdir+$L --top-module tb_s81_pdie_fanout_eq "$@" --Mdir $OUT/$l -o tb $F > $OUT/build_$l.log 2>&1 || { echo "$l BUILD_FAIL"; return 2; }
  $OUT/$l/tb +verilator+seed+3 > $OUT/run_$l.log 2>&1; grep TB_S81_PDIE_FANOUT_EQ $OUT/run_$l.log | tail -1
}
a=$(run base); echo "$a"
m=$(run mut_stale -DRMRPC_MUT_STALE); echo "$m"
k=$(run dkreg -GDKREG=1); echo "$k"
n=$(run dkreg_mut_nodd -GDKREG=1 -DDKREG_MUT_NODD); echo "$n"
v=PASS
case "$a" in *" PASS") ;; *) v=FAIL;; esac
case "$m" in *" FAIL") ;; *) v=FAIL;; esac
case "$k" in *" PASS") ;; *) v=FAIL;; esac
case "$n" in *" FAIL") ;; *) v=FAIL;; esac
echo "PDIE_FANOUT_EQ $v"
[ $v = PASS ]
