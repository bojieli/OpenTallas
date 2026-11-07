#!/bin/bash
# DIE-HEAD-76 hd_lep0N_vC: yosys equivalence of the 0-cycle split composition ot_s81hd_lep0N_split_core (hub + 4
# regions, LOCAL_RST=0) against the built core ot_s81hd_lep0N_noidx_core PAIR=1 (pair child + SRAMs black boxes).
# The txext LEP keeps its now-unused internal lo*_v/_d/_r nets (driven 0 / unread; the real lo_k lives in region k):
# they are blacklisted as compare points; every port, register, SRAM pin and pair pin is compared.
# Usage: head_lep_split_equiv.sh KIT_RTL_DIR REPO OUTDIR   (run inside openroad/orfs; yosys on PATH)
set -euo pipefail
RTL=$1; REPO=$2; OUT=$3; mkdir -p "$OUT"
cmp "$RTL/ot_s81hd_lep_nr.sv" "$REPO/rtl/dsrom_sys/s81_head/generated/ot_s81hd_lep_nr.sv"
FILES=""
for f in ot_dp_cells.sv ot_reset_sync.sv ot_s81_mu72_lnland.sv ot_s81sl_slice_lep.sv ot_pl_land.sv ot_pl_land_field_copies.sv \
         ot_pl_land_kept_enable.sv ot_pl_land_reset_forest.sv ot_link_credit_rx_b64.sv ot_link_credit_tx_rc.sv ot_s81_mu72_land.sv \
         ot_s81hd_lep_nr.sv ot_s81hd_lep0N_core.sv ot_rst_relay.sv ot_rst_relay_tree3.sv ot_sram_oldread_b64.sv \
         ot_sram_showahead_1r1w.sv ot_sram_showahead_b64.sv ot_link_crc32.sv ot_meso_fifo.sv; do
  FILES="$FILES read_verilog -defer -sv -noautowire $RTL/$f;"
done
LIBS=""
for f in ot_sram_1r1w2c_256x64_m1_bb.v ot_sram_1r1w2c_32x64_m1_bb.v ot_sram_1r1w_128x256_m1_r0c0_bb.v \
         ot_sram_1r1w_32x128_m1_r0c0_bb.v ot_sram_1r1w_512x128_m4_r0c0_bb.v ot_s81hd_lep_pair_bb.v; do
  LIBS="$LIBS read_verilog -lib -overwrite -sv -noautowire $RTL/$f;"
done
SPLIT="read_verilog -defer -sv -noautowire $REPO/rtl/dsrom_sys/s81_head/generated/ot_s81hd_lep_split_nr.sv; read_verilog -defer -sv -noautowire $REPO/rtl/dsrom_sys/s81_head/ot_s81hd_lep0N_split.sv;"
PREP="proc; setattr -mod -unset keep_hierarchy *; flatten; opt_clean; memory; opt_clean; async2sync; opt -fast; opt_clean; expose -evert t:ot_sram_* t:ot_s81hd_lep_pair; opt_clean"
yosys -q -l "$OUT/gate.log" -p "verilog_defines -DSYNTHESIS -DOT_COLL_NATIVE32 -DOT_COLL_NATIVE32_OFF; $LIBS $FILES $SPLIT
  read_verilog -defer -sv $(dirname $0)/head_lep_split_eq_tops.sv; hierarchy -check -top eq_gate; $PREP; rename -top gate; stat; select gate; write_rtlil -selected $OUT/gate_raw.il"
sed -e 's/\\w\.g_rg\[\([0-3]\)\]\.u_reg\.u_txl\.g_tx\[/\\w.u.u_lep.u.g_tx[/g' \
    -e 's/\\w\.g_rg\[\([0-3]\)\]\.u_reg\.u_pair/\\w.u.g_pp[\1].u_pair/g' "$OUT/gate_raw.il" > "$OUT/gate.il"
yosys -q -l "$OUT/gold.log" -p "verilog_defines -DSYNTHESIS -DOT_COLL_NATIVE32 -DOT_COLL_NATIVE32_OFF; $LIBS $FILES
  read_verilog -defer -sv $(dirname $0)/head_lep_split_eq_tops.sv; hierarchy -check -top eq_gold; $PREP; rename -top gold; stat; write_rtlil $OUT/gold.il"
yosys -l "$OUT/equiv.log" -p "read_rtlil $OUT/gold.il; read_rtlil $OUT/gate.il;
  equiv_make -blacklist $(dirname $0)/head_lep_split_eq_blacklist.txt gold gate equiv; hierarchy -top equiv; equiv_simple -seq 6; equiv_induct -undef -seq 6; equiv_status -assert"
echo "HEAD_LEP_SPLIT_EQUIV PASS"
