#!/bin/bash
# fill-9 p2 OLK bench (ot_mtp_p2_prefix_path OLK=1, ROOTPIPE=1): run from the source root; $1 = out dir, $2 = case
#  pos   : exact 1280-value PATH (rc 0, P2_OLK_PASS)
#  order : MUT_ORDER transport mutant must be caught (rc 1, P2_OLK_NEG_DETECTED)
#  lk    : MUT_OLK (lockup on the rising edge = one-cycle stale pin view) must be caught (rc 1, P2_OLK_NEG_DETECTED)
set -u; O=${1:?out}; mkdir -p $O; S=$(pwd)
(cd $O && python3 $S/tools/mtp_p2_prefix_fixture.py) || exit 3
D=rtl/experimental/mtp_p2_ordered_20261009
SRCS="$D/ot_mtp_p2_ordered_rows.sv $D/ot_mtp_p2_prefix.sv $D/ot_mtp_p2_prefix_native.sv $D/ot_mtp_p2_prefix_path.sv rtl/v41rom/ot_v41_fadd.sv rtl/common/ot_prefix.sv rtl/common/ot_secded.sv rtl/common/ot_sc_pfifo.sv rtl/model/hbm_pc40_native_sim_20261003/ot_sram_1r1w_128x256_m1_r2c2_sim.sv $D/tb_mtp_p2_prefix_path.sv"
run(){ n=$1; shift; iverilog -g2012 -Irtl/common -s tb_mtp_p2_prefix_path "$@" -o $O/$n.vvp $SRCS || return 9; (cd $O && vvp -n $O/$n.vvp) > $O/$n.log 2>&1; echo "rc=$?" >> $O/$n.log; }
P="-Ptb_mtp_p2_prefix_path.ROOTPIPE=1 -Ptb_mtp_p2_prefix_path.OLK=1"
case ${2:-pos} in
 pos) run olk $P; cat $O/olk.log | tail -3; grep -q '^PATH PASS' $O/olk.log && { echo P2_OLK_PASS; exit 0; }; exit 1;;
 order) run olk_order $P -Ptb_mtp_p2_prefix_path.MUT=2; tail -2 $O/olk_order.log; grep -q '^PATH PASS' $O/olk_order.log || { echo P2_OLK_NEG_DETECTED; exit 1; }; exit 0;;
 lk) run olk_mut $P -Ptb_mtp_p2_prefix_path.MUT=3; tail -2 $O/olk_mut.log; grep -q '^PATH PASS' $O/olk_mut.log || { echo P2_OLK_NEG_DETECTED; exit 1; }; exit 0;;
esac
