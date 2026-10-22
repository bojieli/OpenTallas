#!/bin/bash
# HBM-ELEM13/COLL-GQ R11 benches (Verilator 5.050 = daemon pin); $1 = main|wr2
V=$1; cd "$(dirname "$0")/src" || exit 9
export VERILATOR=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator JOBS=6 PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
XD=""; [[ $V == wr2 ]] && XD="-DOT_COLLQ_SRAM_WR2"
O=$(realpath ../out_$V); mkdir -p $O; : > $O/rc.txt
P=rtl/hbm_accel/generic/collective/p2p
B="env OT_GQ_P192=1 OT_GQ_N32=1"
run(){ n=$1; shift; ( "$@" > $O/$n.log 2>&1; echo "$n rc=$?" >> $O/rc.txt ) & }
run aqx env OT_GQ_P192=1 OT_GQ_N32=1 OT_GQ_XDEFS="$XD" bash $P/run_aq_sram_exact.sh $O/aqx 0
run aqmut env OT_GQ_P192=1 OT_GQ_N32=1 OT_GQ_XDEFS="$XD" bash $P/run_aq_sram_exact.sh $O/aqmut 1
run ia1 $B OT_GQ_XDEFS="$XD" bash $P/run_coll_gq_ia.sh $O/ia1 ia1
run ia2 $B OT_GQ_XDEFS="$XD" bash $P/run_coll_gq_ia.sh $O/ia2 ia2
run ia1_inv $B OT_GQ_XDEFS="$XD -DOT_GQ_CHECK_INV" bash $P/run_coll_gq_ia.sh $O/ia1_inv ia1
run ia2_inv $B OT_GQ_XDEFS="$XD -DOT_GQ_CHECK_INV" bash $P/run_coll_gq_ia.sh $O/ia2_inv ia2
run slot $B OT_GQ_XDEFS="$XD" bash $P/run_coll_gq_ia.sh $O/slot slot
run dep $B OT_GQ_XDEFS="$XD" bash $P/run_coll_gq_ia.sh $O/dep dep
run iaign $B OT_GQ_XDEFS="$XD" bash $P/run_coll_gq_ia.sh $O/iaign iaign
run mut_tllast $B OT_GQ_XDEFS="$XD -DOT_GQ_MUT_TLLAST" bash $P/run_coll_gq_ia.sh $O/mut_tllast ia1
run mut_ohcopy $B OT_GQ_XDEFS="$XD -DOT_GQ_MUT_OH_COPY" bash $P/run_coll_gq_ia.sh $O/mut_ohcopy ia1
run mut_firelate $B OT_GQ_XDEFS="$XD -DOT_GQ_MUT_FIRE_LATE" bash $P/run_coll_gq_ia.sh $O/mut_firelate ia1
run full_inv env OT_GQ_FAN32=1 OT_GQ_S2TOP=1 OT_GQ_P192=1 OT_GQ_N32=1 OT_GQ_XDEFS="$XD -DOT_GQ_CHECK_INV" bash $P/run_coll_gq_bench.sh $O/full_inv
wait
sort $O/rc.txt
