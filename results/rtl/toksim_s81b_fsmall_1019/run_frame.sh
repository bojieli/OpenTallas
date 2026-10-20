#!/bin/bash
# TOKSIM-S81B/FSMALL 10-19: run every vector of one die frame (toksim_fsmall_gen.py output) of op OP on the RELEASE frame
# bench exe of its die instance (build_seq.sh: release 19bf4121e die.v master + lk), the compiler-of-record check per phase
# (xs_place.py check, or lower_xs.py check for the p0 a_proj programme: every returned word vs golden segment tree, row
# coverage, cycle-exact vs the compiled return calendar, fixture BF16 tie), then (>1 phase) the back-to-back phase
# sequence swept over the go period, checked by toksim_fgu_check.py seq.
# usage: run_frame.sh <layer> <frame> <op> ["PERS"]   (R = staging root on ot-epyc9)
set -u
R=/srv/opentallas-scratch/claude/toksim-s81b-fsmall; L=$1; F=$2; OP=$3; PERS=${4:-"600 400 300 260 220 200 180 160 140"}
V=$R/vec/$L/$F; O=$R/run/$L/$F; mkdir -p $O; Q=tools/s81_dv/layer_prog/qf_producer
case $F in u_f_?L00|u_f_?R00) B=s_h9nx_e5;; u_f_?L01|u_f_?R01) B=s_h10_e2;; u_f_?L02|u_f_?R02) B=s_h9MX_e1;; u_f_?L03|u_f_?R03) B=s_h9nx_e2;; esac
X=$R/$B/obj/Vtb_toksim_fgu_seq; [ -x $X ] || { echo "NO_EXE $X"; exit 3; }
cd $R/src
PH=$(python3 -c "import json;d=json.load(open('$V/frame.json'));print(' '.join('p%d'%p['phase'] for p in d['phases'] if p['op']=='$OP'))")
for n in $PH; do
  VD=$V/$n
  $X $(sed "s#+OT_ROM_DIR=[^ ]*#+OT_ROM_DIR=$VD#" $VD/ARGS) > $O/run_$n.log 2>&1; rc=$?
  CK=xs_place; [ -f $VD/CHECKER ] && CK=$(cat $VD/CHECKER)
  python3 tools/s81_dv/layer_prog/$CK.py check --dir $VD --log $O/run_$n.log > $O/check_$n.txt 2>&1; crc=$?
  echo "FSMALL_RUN $L $F $OP $n exe $B rc=$rc check_rc=$crc $(python3 $Q/toksim_fgu_check.py single --log $O/run_$n.log) | $(tail -n 1 $O/check_$n.txt)"
done
S=$(python3 $Q/toksim_fsmall_seq.py --vec $V --op $OP); echo "$S"
if [ "${S%% *}" = SEQ ]; then
  read _ SD NPH K OPS PH0 <<< "$S"
  REF=$(grep -m1 -oP '^GO 0 \K\d+' $O/run_p$PH0.log)
  for P in $PERS; do
    T=$((NPH * P + 1200))
    $X +OT_ROM_DIR=$SD +T=$T +K=$K +OPS=$OPS +PH=$PH0 +NPH=$NPH +PER=$P > $O/run_seq_P$P.log 2>&1
    echo "FSMALL_SEQ $L $F $OP $(python3 $Q/toksim_fgu_check.py seq --seq $SD --vec $V --log $O/run_seq_P$P.log --out $O/res_seq_P$P.json --per $P --ref-go $REF 2>&1 | tail -1)"
  done
fi
gzip -f $O/run_*.log
echo FSMALL_FRAME_DONE $L $F $OP
