#!/bin/bash
# run_kp4_gate.sh <src root> <out dir>: F10 gate of the S81 die-link KP4 FEC RTL (ot_s81_kp4_enc / _dec) vs
# tools/s81_link/rs544.py.  base must PASS; enc MUT 1 and dec MUT 2 must FAIL.  Prints KP4_GATE PASS|FAIL.
set -u
SRC=$1; OUT=$2; mkdir -p $OUT
python3 $SRC/tools/s81_link/rs544.py selftest > $OUT/ref_selftest.log 2>&1 || { echo "KP4_GATE FAIL (reference selftest)"; exit 1; }
python3 $SRC/tools/s81_link/rs544.py vectors $OUT/vec.hex --n 16 --seed 5 > /dev/null
F="$SRC/rtl/dsrom_sys/s81_link/ot_s81_kp4_common.sv $SRC/rtl/dsrom_sys/s81_link/ot_s81_kp4_enc.sv $SRC/rtl/dsrom_sys/s81_link/ot_s81_kp4_bm.sv $SRC/rtl/dsrom_sys/s81_link/ot_s81_kp4_dsyn.sv $SRC/rtl/dsrom_sys/s81_link/ot_s81_kp4_ddly.sv $SRC/rtl/dsrom_sys/s81_link/ot_s81_kp4_dchn.sv $SRC/rtl/dsrom_sys/s81_link/ot_s81_kp4_dout.sv $SRC/rtl/dsrom_sys/s81_link/ot_s81_kp4_dec.sv $SRC/physical/asap7_memory_macros/ot_sram_1r1w2c_64x546_m1/ot_sram_1r1w2c_64x546_m1.v $SRC/physical/asap7_memory_macros/ot_sram_1r1w_32x546_m1/ot_sram_1r1w_32x546_m1.v $SRC/rtl/dsrom_sys/s81_link/tb_s81_kp4.sv"
run() { l=$1; shift
  verilator --binary --timing -j 16 -Wno-fatal -Wno-WIDTH -Wno-lint -Wno-style -Wno-UNOPTFLAT +incdir+$SRC/rtl/dsrom_sys/s81_link --top-module tb_s81_kp4 "$@" --Mdir $OUT/$l -o tb $F > $OUT/build_$l.log 2>&1 || { echo "$l BUILD_FAIL"; return 2; }
  $OUT/$l/tb +vec=$OUT/vec.hex +verilator+seed+11 > $OUT/run_$l.log 2>&1; grep TB_S81_KP4 $OUT/run_$l.log | tail -1
}
a=$(run base) ; echo "$a"
m1=$(run emut -GEMUT=1); echo "$m1"
m2=$(run dmut -GDMUT=2); echo "$m2"
v=PASS
case "$a" in *" PASS") ;; *) v=FAIL;; esac
case "$m1" in *" FAIL") ;; *) v=FAIL;; esac
case "$m2" in *" FAIL") ;; *) v=FAIL;; esac
echo "KP4_GATE $v"
[ $v = PASS ]
