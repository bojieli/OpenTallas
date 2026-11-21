#!/bin/bash
# FAM-S81-SLICE-R2: default-off (no OT_S81SL_XS4_WREG) equivalence of ot_s81sl_xs4: main 39d243610b vs the R2 file.
# usage: xs4_lec.sh CLONE GOLD_SV OUTDIR
set -euo pipefail
C=$1; G=$2; O=$3; mkdir -p $O
Y=~/.local/opentallas-tools/yosys-0.68/bin/yosys; [ -x $Y ] || Y=yosys
M=$C/physical/asap7_memory_macros_v2
SUP="rtl/lib/ot_rst_relay.sv rtl/v41rom/ot_v41_kreg.sv rtl/common/ot_prefix.sv rtl/dsrom_sys/s81_static_control/ot_s81_pq_calendar_reader.sv rtl/dsrom_sys/s81_ph/pq/ot_s81_pq_stream_rom4_sel.sv rtl/dsrom_sys/s81_die_bind/dsfd_sp_pq_n.sv"
BB="$M/ot_rom_4096x72_m8/ot_rom_4096x72_m8_bb.v $M/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2_bb.v $M/ot_sram_1r1w2c_128x64_m1/ot_sram_1r1w2c_128x64_m1_bb.v"
side() {  # name file
  echo "design -reset"
  for b in $BB; do echo "read_verilog -lib $b"; done
  for f in $SUP; do echo "read_verilog -sv -DSYNTHESIS -DDSFD_PQ_STATIC_X2 $C/$f"; done
  echo "read_verilog -sv -DSYNTHESIS -DDSFD_PQ_STATIC_X2 $2"
  echo "hierarchy -check -top ot_s81sl_xs4"
  echo "proc; memory; flatten; opt_clean"
  echo "rename ot_s81sl_xs4 $1"
  echo "design -stash $1"
}
{ side gold $G; side gate $C/rtl/dsrom_sys/s81_dv/slice/ot_s81sl_xs4.sv
  echo "design -reset"
  for b in $BB; do echo "read_verilog -lib $b"; done
  echo "design -copy-from gold -as gold gold"
  echo "design -copy-from gate -as gate gate"
  echo "equiv_make gold gate eq"
  echo "hierarchy -top eq"
  echo "equiv_simple -seq 2"
  echo "equiv_induct -seq 2"
  echo "tee -o $O/equiv_status.txt equiv_status"
  echo "equiv_status -assert"
} > $O/lec.ys
$Y -q -l $O/lec.log -s $O/lec.ys && echo XS4_LEC_DEFAULT_OFF EQUIVALENT || { tail -20 $O/lec.log; echo XS4_LEC_DEFAULT_OFF FAIL; exit 1; }
