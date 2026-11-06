#!/bin/bash
# DIE-HEAD-71 11-05 ctlrq: new RTL at the default params (opt-in reset forms off) == old (branch HEAD) RTL,
# register-matched sequential equivalence (equiv_make / equiv_simple -seq 2 / equiv_induct / equiv_status -assert).
# usage (repo root): [ON_REF=<ref>] tools/s81_head/ctl_rst_eq.sh OLD_REF OUTDIR   OLD_REF = the commit before the ctlrq change.
# Scope: each changed module with its opt-in at 0 (beat_tx HOLD_RST at 7 W/N/P/IDLE_ZERO/MUT/HOLD_REAL points,
# host276_tx, lrx_qr Q_RST=0 vs lrx, ot_dsrom_mtp_seq_fan, dsfd_mtp_seq_fan, whole ot_s81hd_ctl_core DATA_RST=0).
# The SRAM macro is a port-only blackbox on both sides.  The opt-in = 1 forms are covered by the benches + kit LEC.
set -u; S=$(pwd); REF=${1:?OLD_REF}; OUT=$(realpath -m ${2:?OUTDIR}); mkdir -p $OUT/old; Y=${YOSYS:-$HOME/.local/opentallas-tools/bin/yosys}; rc=0
H=$S/rtl/dsrom_sys/s81_head; M=$S/rtl/dsrom_sys/mtp; OL=$OUT/old
for f in s81_head/ot_s81hd_beat_link s81_head/ot_s81hd_host276 s81_head/ot_s81hd_ctl_core s81_head/ot_s81hd_ctl_hsf0_static mtp/dsfd_mtp_tops mtp/ot_dsrom_mtp_seq; do
  git show $REF:rtl/dsrom_sys/$f.sv > $OL/$(basename $f).sv || exit 2; done
SP=$S/physical/asap7_memory_macros_v2/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v
{ echo "(* blackbox *)"; sed -n '/^module ot_sram_1r1w_64x512_m1_r2c2 (/,/^);/p' $SP | sed 's/output reg /output wire/'; echo "endmodule"; } > $OUT/sram_bb.v
cd $OUT
COMMON_H="$H/ot_s81hd_static_issue.sv $H/ot_s81hd_util.sv $H/ot_s81hd_best64.sv $H/ot_s81hd_mesh_ep_core.sv $H/ot_s81hd_ar_control_hsf0.sv $H/ot_s81hd_rank_merge_hsf0.sv $H/ot_s81hd_result_landing_hsf0.sv $H/ot_s81hd_fault_state_hsf0.sv $M/ot_dsrom_mtp_link_pair.sv $S/rtl/lib/ot_rst_relay_tree3.sv"
SRAM=$OUT/sram_bb.v  # port-only blackbox, the same on both sides (the macro model is not part of the change)
NEWF="$H/ot_s81hd_beat_link.sv $H/ot_s81hd_host276.sv $H/ot_s81hd_ctl_core.sv $H/ot_s81hd_ctl_hsf0_static.sv $M/dsfd_mtp_tops.sv $M/ot_dsrom_mtp_seq.sv"
OLDF="$OL/ot_s81hd_beat_link.sv $OL/ot_s81hd_host276.sv $OL/ot_s81hd_ctl_core.sv $OL/ot_s81hd_ctl_hsf0_static.sv $OL/dsfd_mtp_tops.sv $OL/ot_dsrom_mtp_seq.sv"
eq() {  # name top_old top_new "chparam-old" "chparam-new"
  cat > $1.ys <<Y
read_verilog -sv $SRAM
read_verilog -sv -DSYNTHESIS $OLDF $COMMON_H
$4
hierarchy -top $2; proc; flatten; opt_clean; rename -top gold; design -stash g
read_verilog -sv $SRAM
read_verilog -sv -DSYNTHESIS $NEWF $COMMON_H
$5
hierarchy -top $3; proc; flatten; opt_clean; rename -top gate; design -stash h
design -copy-from g -as gold gold
design -copy-from h -as gate gate
equiv_make gold gate eq; hierarchy -top eq; async2sync
equiv_simple -seq 2; equiv_induct; equiv_status -assert
Y
  local t0=$(date +%s); timeout ${TO:-3600} $Y -q -l $1.log $1.ys >/dev/null 2>&1; r=$?
  echo "== $1 rc=$r $(( $(date +%s)-t0 ))s $(grep -o 'Found [0-9]* \$equiv cells.*' $1.log | tail -1) | $(grep -o 'Of those cells [0-9]* are proven and [0-9]* are unproven' $1.log | tail -1)"; [ $r = 0 ] || rc=1
}
BT=ot_s81hd_beat_tx
for pt in "r553 553 2 277 0 0 0" "b97 97 2 62 1 0 1" "h553 553 3 273 1 0 1" "h553hr0 553 3 273 1 0 0" "h553m1 553 3 273 1 1 1" "h1104 1104 4 276 0 0 0" "m64 64 1 64 0 0 0"; do set -- $pt
  c="chparam -set W $2 -set N $3 -set P $4 -set IDLE_ZERO $5 -set MUT $6 -set HOLD_REAL $7 $BT"
  eq bt_$1 $BT $BT "$c" "$c; chparam -set HOLD_RST 0 $BT"; done
eq h276 ot_s81hd_host276_tx ot_s81hd_host276_tx "chparam -set IDLE_ZERO 1 -set HOLD_REAL 1 ot_s81hd_host276_tx" "chparam -set IDLE_ZERO 1 -set HOLD_REAL 1 -set HOLD_RST 0 ot_s81hd_host276_tx"
eq lrx ot_dsrom_mtp_lrx ot_dsrom_mtp_lrx_qr "chparam -set W 512 ot_dsrom_mtp_lrx" "chparam -set W 512 -set Q_RST 0 ot_dsrom_mtp_lrx_qr"
eq seqcore ot_dsrom_mtp_seq_fan ot_dsrom_mtp_seq_fan "" "chparam -set DATA_RST 0 ot_dsrom_mtp_seq_fan"
eq seqtop dsfd_mtp_seq_fan dsfd_mtp_seq_fan "" "chparam -set DATA_RST 0 dsfd_mtp_seq_fan"
TO=${TO_BIG:-5400} eq ctl_core ot_s81hd_ctl_core ot_s81hd_ctl_core "" "chparam -set DATA_RST 0 ot_s81hd_ctl_core"
# ON_REF (optional): ot_dsrom_mtp_seq_fan with DATA_RST = 1 here == at ON_REF (the opt-in form itself across a change;
# 11-05 step 2: the event position read as the ef slice instead of its ep_ twin, vs 384d2dbed72)
if [ -n "${ON_REF:-}" ]; then
  git -C $S show $ON_REF:rtl/dsrom_sys/mtp/ot_dsrom_mtp_seq.sv > $OL/seq_on_ref.sv || exit 2
  SAVE="$OLDF"; OLDF="$OL/seq_on_ref.sv"; NEWF0="$NEWF"; NEWF="$M/ot_dsrom_mtp_seq.sv"
  eq seqcore_on ot_dsrom_mtp_seq_fan ot_dsrom_mtp_seq_fan "chparam -set DATA_RST 1 ot_dsrom_mtp_seq_fan" "chparam -set DATA_RST 1 ot_dsrom_mtp_seq_fan"
  OLDF="$SAVE"; NEWF="$NEWF0"
fi
echo "EQRST rc=$rc $(date)"; exit $rc
