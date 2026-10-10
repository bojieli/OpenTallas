#!/bin/bash
# run_ctrl_chain.sh <src root> <out dir>: tb_s81_ctrl_chain (Verilator 5).  Lines: base (PASS), +forge (PASS: the
# guard drops the forged message, F_SRC), MUT=1 SOURCE ignores STOP (must FAIL), guard mutant NOSRC +forge (must FAIL)
set -u
SRC=$1; OUT=$2; mkdir -p $OUT
S=$SRC/rtl/dsrom_sys
FILES="$S/s81_ctrl/ot_s81_stage_seq.sv $S/s81_ctrl/ot_s81_pkg_ctrl.sv $S/s81_ctrl/ot_s81_stage_guard.sv $S/s81_ctrl/ot_s81_hop_tx.sv
 $S/s81_ctrl/ot_s81_stop.sv $S/s81_ctrl/ot_s81_host_cq.sv $S/s81_ctrl/ot_s81_ctrl.sv $S/ot_dsrom_stall_export.sv
 $S/ot_dsrom_link_ct.sv $S/ot_dsrom_link_chan.sv $SRC/rtl/link/ot_link_crc32.sv $S/s81_ctrl/test/tb_s81_ctrl_chain.sv"
bld() {   # <dir> <extra args>
  local B=$OUT/$1; shift; mkdir -p $B
  verilator --binary --timing -Wno-fatal -Wno-WIDTH -Wno-lint -Wno-MULTIDRIVEN -I$S/s81_ctrl --top-module tb_s81_ctrl_chain \
    "$@" --Mdir $B -o tb $FILES > $B/build.log 2>&1 || { echo BUILD_FAIL $B; grep -m10 -i error $B/build.log; exit 1; }
}
bld chain_m0 -GMUT=0; bld chain_m1 -GMUT=1; bld chain_nosrc -GMUT=0 -DS81_GUARD_MUTANT_NOSRC
LOG=$OUT/chain.log; : > $LOG
echo "# base"            >> $LOG; timeout 600 $OUT/chain_m0/tb          2>&1 | grep -E "TB_S81|^ERR" >> $LOG
echo "# forge"           >> $LOG; timeout 600 $OUT/chain_m0/tb +forge   2>&1 | grep -E "TB_S81|^ERR" >> $LOG
echo "# MUT1 (expect FAIL)"  >> $LOG; timeout 600 $OUT/chain_m1/tb      2>&1 | grep -E "TB_S81" >> $LOG
echo "# NOSRC +forge (expect FAIL)" >> $LOG; timeout 600 $OUT/chain_nosrc/tb +forge 2>&1 | grep -E "TB_S81" >> $LOG
cat $LOG
