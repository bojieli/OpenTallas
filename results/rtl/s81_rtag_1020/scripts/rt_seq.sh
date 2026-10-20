#!/bin/bash
# S81-RTAG: one static BF phase sequence (FSEQ vehicle tb_toksim_fgu_seq +RETIRE +PHASE_VM) on a frame exe built from
# the S81-RTAG source (XP prefix: t = trace SOQ 0, s<SWD> = SOQ 1).  usage: rt_seq.sh VECDIR(L0/<frame>) FRAME NAME OP XP "PERS"
set -u
R=/srv/opentallas-scratch/claude/s81-rtag-1020; VD=$1; F=$2; NM=$3; OP=$4; XP=$5; PERS=$6; PERS=${PERS//,/ }
export PYTHONDONTWRITEBYTECODE=1
case $F in u_f_?L00|u_f_?R00) B=${XP}_h9nx_e5;; u_f_?L01|u_f_?R01) B=${XP}_h10_e2;; u_f_?L02|u_f_?R02) B=${XP}_h9MX_e1;; u_f_?L03|u_f_?R03) B=${XP}_h9nx_e2;; esac
X=$R/$B/obj/Vtb_toksim_fgu_seq; [ -x $X ] || { echo "NO_EXE $X"; exit 3; }
O=$R/run/$F/${NM}_$XP; mkdir -p $O; cd $R/src; Q=tools/s81_dv/layer_prog/qf_producer
echo "EXE $B $(sha256sum $X | cut -c1-16) $(cat $R/$B/verilator.version)"
S=$(python3 $Q/toksim_fseq_seqops.py --vec $VD --name ${NM}_$XP --phase-vm --ops $OP); echo "$S"
[ "${S%% *}" = SEQ ] || { echo NOSEQ; exit 2; }
read _ SD NPH K OPS PH0 <<< "$S"
for P in $PERS; do
  T=$((NPH * P + 1500)); tg=P$P
  timeout 1800 $X +OT_ROM_DIR=$SD +T=$T +K=$K +OPS=$OPS +PH=$PH0 +NPH=$NPH +PER=$P +RETIRE=1 +PHASE_VM=1 > $O/run_seq_$tg.log 2>&1; rc=$?
  echo "RT_SEQ $NM $F $XP rc=$rc P=$P $(python3 $Q/toksim_fgu_check.py seq --seq $SD --vec $VD --log $O/run_seq_$tg.log --out $O/res_seq_$tg.json --per $P --ref-go 63 2>&1 | tail -1)"
done
gzip -f $O/run_*.log
echo RT_SEQ_DONE $NM $F $XP
