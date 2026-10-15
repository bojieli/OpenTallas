#!/bin/bash
# run_hbm_gate.sh <src root> <out dir>: F10/HBM gate of the S81 HBM macro RTL (controller) over the behavioural PHY /
# device: base must PASS, MUT 1 (tRCD) must FAIL.  Prints HBM_GATE PASS|FAIL.
set -u
SRC=$1; OUT=$2; mkdir -p $OUT
F="$SRC/rtl/dsrom_sys/s81_link/ot_s81_hbm_pcc.sv $SRC/rtl/dsrom_sys/s81_link/ot_hbm3e_phy_v41x_aw30_e8p5.sv $SRC/rtl/dsrom_sys/s81_link/tb_s81_hbm.sv"
run() { l=$1; shift
  verilator --binary --timing -j 16 -Wno-fatal -Wno-WIDTH -Wno-lint -Wno-style -Wno-UNOPTFLAT --top-module tb_s81_hbm "$@" --Mdir $OUT/$l -o tb $F > $OUT/build_$l.log 2>&1 || { echo "$l BUILD_FAIL"; return 2; }
  $OUT/$l/tb +verilator+seed+5 > $OUT/run_$l.log 2>&1; grep TB_S81_HBM $OUT/run_$l.log | tail -1
}
a=$(run base); echo "$a"
m=$(run mut1 -GMUT=1); echo "$m"
v=PASS
case "$a" in *" PASS") ;; *) v=FAIL;; esac
case "$m" in *" FAIL") ;; *) v=FAIL;; esac
echo "HBM_GATE $v"
[ $v = PASS ]
