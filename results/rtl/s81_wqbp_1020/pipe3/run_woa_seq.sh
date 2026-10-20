#!/bin/bash
# S81-WQBP part 2 (S81-PIPE3 work, 10-20): attn.wo_a as ONE overlapped phase sequence (row-batch pipelining: go i at
# go0 + i x P, static) on the RELEASE frame RTL, instead of the serial per-phase sum (TOKSIM-S81B/FWOA 4224 = 12 x 352).
# Vehicle = TOKSIM-S81C/FSEQ (tb_toksim_fgu_seq +RETIRE +PHASE_VM: each BF phase = one K segment of x reloaded at its go;
# release 19bf4121e frame exes v_h9nx_e5 / v_h10_e2, Verilator 5.050) driven by the FWOA wo_a phase vectors
# (xs_place gen, released L0 fixture, real rank-0 rows).  Checker = toksim_fgu_check.py seq (golden segment tree
# bit-exact per row, coverage, cycle-exact calendar).  usage: run_woa_seq.sh LEG FRAME "PERS"
set -u
LEG=$1; F=$2; PERS=$3
D=/srv/opentallas-scratch/claude/s81-wqbp/pipe3; FS=/srv/opentallas-scratch/claude/toksim-s81c-fseq; WA=/srv/opentallas-scratch/claude/toksim-s81b-fwoa/$LEG
export PYTHONDONTWRITEBYTECODE=1
V=$D/vec/L0/$F; O=$D/run/$F/woa; mkdir -p $O $V
[ -f $V/frame.json ] || { cp $WA/frame/frame.json $V/; for p in $(seq 5 16); do cp -r $WA/vec/p$p $V/; done; }
case $F in u_f_?L00|u_f_?R00) B=v_h9nx_e5;; u_f_?L01|u_f_?R01) B=v_h10_e2;; *) echo NO_EXE_MAP; exit 3;; esac
X=$FS/$B/obj/Vtb_toksim_fgu_seq; [ -x $X ] || { echo "NO_EXE $X"; exit 3; }
echo "EXE $B $(sha256sum $X | cut -c1-16) $(cat $FS/$B/verilator.version 2>/dev/null)"
cd $FS/src2; Q=tools/s81_dv/layer_prog/qf_producer
S=$(python3 $Q/toksim_fseq_seqops.py --vec $V --name woa --phase-vm --ops attn.wo_a); echo "$S"
[ "${S%% *}" = SEQ ] || { echo NOSEQ; exit 2; }
read _ SD NPH K OPS PH0 <<< "$S"
for P in $PERS; do
  T=$((NPH * P + 1500)); tg=P$P
  timeout 1800 $X +OT_ROM_DIR=$SD +T=$T +K=$K +OPS=$OPS +PH=$PH0 +NPH=$NPH +PER=$P +RETIRE=1 +PHASE_VM=1 > $O/run_seq_$tg.log 2>&1; rc=$?
  echo "WOA_SEQ $LEG $F rc=$rc P=$P $(python3 $Q/toksim_fgu_check.py seq --seq $SD --vec $V --log $O/run_seq_$tg.log --out $O/res_seq_$tg.json --per $P --ref-go 63 2>&1 | tail -1)"
done
gzip -f $O/run_*.log
echo WOA_SEQ_DONE $LEG $F
