#!/bin/bash
# run_pdie_link_gate.sh <src root> <out dir>: F10 gate of the S81 die link macros' RTL (ot_pdie_serdes: KP4 FEC +
# rate matching over a behavioural PMA with pad bit errors; ot_pdie_ucie) between two plesiochronous dies, plus the
# KP4 codec gate.  serdes / ucie must PASS, serdes DMUT 2 must FAIL.  Prints PDIE_LINK_GATE PASS|FAIL.
set -u
SRC=$1; OUT=$2; mkdir -p $OUT
F="$SRC/rtl/dsrom_sys/s81_link/ot_s81_kp4_common.sv $SRC/rtl/dsrom_sys/s81_link/ot_s81_kp4_enc.sv $SRC/rtl/dsrom_sys/s81_link/ot_s81_kp4_bm.sv $SRC/rtl/dsrom_sys/s81_link/ot_s81_kp4_dsyn.sv $SRC/rtl/dsrom_sys/s81_link/ot_s81_kp4_ddly.sv $SRC/rtl/dsrom_sys/s81_link/ot_s81_kp4_dchn.sv $SRC/rtl/dsrom_sys/s81_link/ot_s81_kp4_dout.sv $SRC/rtl/dsrom_sys/s81_link/ot_s81_kp4_dec.sv $SRC/physical/asap7_memory_macros/ot_sram_1r1w2c_64x546_m1/ot_sram_1r1w2c_64x546_m1.v $SRC/physical/asap7_memory_macros/ot_sram_1r1w_32x546_m1/ot_sram_1r1w_32x546_m1.v $SRC/rtl/dsrom_sys/s81_link/ot_pdie_serdes.sv $SRC/rtl/dsrom_sys/s81_link/tb_s81_pdie_link.sv"
run() { l=$1; shift
  verilator --binary --timing -j 16 -Wno-fatal -Wno-WIDTH -Wno-lint -Wno-style -Wno-UNOPTFLAT +incdir+$SRC/rtl/dsrom_sys/s81_link --top-module tb_s81_pdie_link "$@" --Mdir $OUT/$l -o tb $F > $OUT/build_$l.log 2>&1 || { echo "$l BUILD_FAIL"; return 2; }
  $OUT/$l/tb +verilator+seed+3 > $OUT/run_$l.log 2>&1; grep TB_S81_PDIE $OUT/run_$l.log | tail -1
}
a=$(run serdes -GSERDES=1); echo "$a"
b=$(run ucie -GSERDES=0); echo "$b"
m=$(run serdes_dmut -GSERDES=1 -GDMUT=2); echo "$m"
bash $SRC/rtl/dsrom_sys/s81_link/run_kp4_gate.sh $SRC $OUT/kp4 | tail -1 > $OUT/kp4.verdict; cat $OUT/kp4.verdict
v=PASS
case "$a" in *" PASS") ;; *) v=FAIL;; esac
case "$b" in *" PASS") ;; *) v=FAIL;; esac
case "$m" in *" FAIL") ;; *) v=FAIL;; esac
grep -q "KP4_GATE PASS" $OUT/kp4.verdict || v=FAIL
echo "PDIE_LINK_GATE $v"
[ $v = PASS ]
