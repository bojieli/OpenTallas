#!/bin/bash
# HARD-S81-SERDES-1: KP4 gate (tb_s81_kp4 vs rs544.py vectors) under a define set.  usage: kp4gate.sh OUT label "defs" (in the verilator image)
SRC=/srv/opentallas-scratch2/claude/hard-s81-serdes-1/wt; OUT=$1; l=$2; shift 2; mkdir -p $OUT; Lk=$SRC/rtl/dsrom_sys/s81_link; M=$SRC/physical/asap7_memory_macros
[ -f $OUT/vec.hex ] || python3 $SRC/tools/s81_link/rs544.py vectors $OUT/vec.hex --n 16 --seed 5 > /dev/null
d=""; for x in "$@"; do d="$d +define+$x"; done
verilator --binary --timing -j 8 -Wno-fatal -Wno-WIDTH -Wno-lint -Wno-style -Wno-UNOPTFLAT +incdir+$Lk --top-module tb_s81_kp4 $d --Mdir $OUT/$l -o tb $Lk/ot_s81_kp4_common.sv $Lk/ot_s81_kp4_enc.sv $Lk/ot_s81_kp4_bm.sv $Lk/ot_s81_kp4_dsyn.sv $Lk/ot_s81_kp4_ddly.sv $Lk/ot_s81_kp4_dchn.sv $Lk/ot_s81_kp4_dout.sv $Lk/ot_s81_kp4_dec.sv $M/ot_sram_1r1w2c_64x546_m1/ot_sram_1r1w2c_64x546_m1.v $M/ot_sram_1r1w_32x546_m1/ot_sram_1r1w_32x546_m1.v $Lk/tb_s81_kp4.sv > $OUT/build_$l.log 2>&1 || { echo "$l BUILD_FAIL"; grep -m4 "%Error" $OUT/build_$l.log; exit 2; }
$OUT/$l/tb +vec=$OUT/vec.hex +verilator+seed+11 > $OUT/run_$l.log 2>&1; echo "$l: $(grep TB_S81_KP4 $OUT/run_$l.log | tail -1)"
