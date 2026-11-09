#!/bin/bash
# DIE-HEAD-84 11-07: the opt-in leg stages at their defaults (KTX/KRX/TXI/PIN/POUT/PLW = 0) leave the hd_lep0N core
# unchanged.  yosys equivalence of ot_s81hd_lep0N_noidx_core PAIR=1 (pair child + SRAMs black boxes):
# gold = OLD wrapper + OLD generated ot_s81hd_lep_nr.sv, gate = NEW wrapper + NEW generated, both at default parameters.
# Usage: head_lepk_default_equiv.sh KIT_RTL_DIR OLD_DIR NEW_DIR OUTDIR   (OLD_DIR / NEW_DIR hold ot_s81hd_lep0N_core.sv +
# ot_s81hd_lep_nr.sv; every other source comes from KIT_RTL_DIR)
set -euo pipefail
RTL=$1; OLD=$2; NEW=$3; OUT=$4; mkdir -p "$OUT"
common() {
  local s=""
  for f in ot_dp_cells.sv ot_reset_sync.sv ot_s81_mu72_lnland.sv ot_s81sl_slice_lep.sv ot_pl_land.sv ot_pl_land_field_copies.sv \
           ot_pl_land_kept_enable.sv ot_pl_land_reset_forest.sv ot_link_credit_rx_b64.sv ot_link_credit_tx_rc.sv ot_s81_mu72_land.sv \
           ot_rst_relay.sv ot_rst_relay_tree3.sv ot_sram_oldread_b64.sv ot_sram_showahead_1r1w.sv ot_sram_showahead_b64.sv \
           ot_link_crc32.sv ot_meso_fifo.sv; do s="$s read_verilog -defer -sv -noautowire $RTL/$f;"; done
  for f in ot_sram_1r1w2c_256x64_m1_bb.v ot_sram_1r1w2c_32x64_m1_bb.v ot_sram_1r1w_128x256_m1_r0c0_bb.v \
           ot_sram_1r1w_32x128_m1_r0c0_bb.v ot_sram_1r1w_512x128_m4_r0c0_bb.v ot_s81hd_lep_pair_bb.v; do
    s="$s read_verilog -lib -overwrite -sv -noautowire $RTL/$f;"; done
  echo "$s"
}
PREP="proc; setattr -mod -unset keep_hierarchy *; flatten; opt_clean; memory; opt_clean; async2sync; opt -fast; opt_clean; expose -evert t:ot_sram_* t:ot_s81hd_lep_pair; opt_clean"
for side in gold gate; do
  D=$OLD; [ $side = gate ] && D=$NEW
  yosys -q -l "$OUT/$side.log" -p "verilog_defines -DSYNTHESIS -DOT_COLL_NATIVE32 -DOT_COLL_NATIVE32_OFF; $(common)
    read_verilog -defer -sv -noautowire $D/ot_s81hd_lep_nr.sv; read_verilog -defer -sv -noautowire $D/ot_s81hd_lep0N_core.sv;
    hierarchy -check -top ot_s81hd_lep0N_noidx_core -chparam PAIR 1; $PREP; rename -top $side; stat; write_rtlil $OUT/$side.il"
done
yosys -l "$OUT/equiv.log" -p "read_rtlil $OUT/gold.il; read_rtlil $OUT/gate.il;
  equiv_make gold gate equiv; hierarchy -top equiv; equiv_simple -seq 4; equiv_induct -undef -seq 4; equiv_status -assert"
echo "HEAD_LEPK_DEFAULT_EQUIV PASS"
