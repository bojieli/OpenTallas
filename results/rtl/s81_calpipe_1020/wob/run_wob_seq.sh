#!/bin/bash
# S81-CALPIPE 10-20: attn.wo_b's 4 FP8 field phases of one frame as ONE static go sequence (go i at go0 + i x P, the
# compiler's pipelined calendar), on the RELEASE frame RTL, instead of the serial per-phase sum (FWOA 4 x 316).
# Vehicle = TOKSIM-S81C/FSEQ tb_toksim_fgu_seq +RETIRE (release 19bf4121e frame exes v_h9nx_e5 / v_h10_e2, Verilator
# 5.050), inputs = the TOKSIM-S81B/FWOA wo_b phase vectors p1..p4 (xs_place gen, released L0 fixture, real rank-0 rows;
# all four phases read the same x).  Checker = toksim_fgu_check.py seq (per-row golden segment tree bit-exact, coverage,
# cycle-exact calendar).  Negative control XCORRUPT: one x word sign-flipped in vm.hex (bit 31; a bit-0 flip lands in the unused low half and PASSED, run 1) at the floor period -> must FAIL.
# usage: run_wob_seq.sh LEG FRAME "PERS" [XCORRUPT_P]
set -u
LEG=$1; F=$2; PERS=$3; XC=${4:-}
D=/srv/opentallas-scratch/claude/s81-calpipe/wob; FS=/srv/opentallas-scratch/claude/toksim-s81c-fseq; WA=/srv/opentallas-scratch/claude/toksim-s81b-fwoa/$LEG
export PYTHONDONTWRITEBYTECODE=1
V=$D/vec/L0/$F; O=$D/run/$F; mkdir -p $O $V
[ -f $V/frame.json ] || { cp $WA/frame/frame.json $V/; for p in 1 2 3 4; do cp -r $WA/vec/p$p $V/; done; }
case $F in u_f_?L00|u_f_?R00) B=v_h9nx_e5;; u_f_?L01|u_f_?R01) B=v_h10_e2;; *) echo NO_EXE_MAP; exit 3;; esac
X=$FS/$B/obj/Vtb_toksim_fgu_seq; [ -x $X ] || { echo "NO_EXE $X"; exit 3; }
echo "EXE $B $(sha256sum $X | cut -c1-16) $(cat $FS/$B/verilator.version 2>/dev/null)"
cd $FS/src2; Q=tools/s81_dv/layer_prog/qf_producer
S=$(python3 $Q/toksim_fseq_seqops.py --vec $V --name wob --ops attn.wo_b); echo "$S"
[ "${S%% *}" = SEQ ] || { echo NOSEQ; exit 2; }
read _ SD NPH K OPS PH0 <<< "$S"
run1() { # tag P romdir
  local tg=$1 P=$2 RD=$3 T=$(( NPH * $2 + 1500 ))
  timeout 1800 $X +OT_ROM_DIR=$RD +T=$T +K=$K +OPS=$OPS +PH=$PH0 +NPH=$NPH +PER=$P +RETIRE=1 > $O/run_seq_$tg.log 2>&1; local rc=$?
  echo "WOB_SEQ $LEG $F $tg rc=$rc P=$P $(python3 $Q/toksim_fgu_check.py seq --seq $SD --vec $V --log $O/run_seq_$tg.log --out $O/res_seq_$tg.json --per $P --ref-go 63 2>&1 | tail -1)"
}
for P in $PERS; do run1 P$P $P $SD; done
if [ -n "$XC" ]; then
  C=$D/xc/$F; rm -rf $C; mkdir -p $C; cp -r $SD/. $C/
  python3 - $C/vm.hex <<'PY'
import sys; p=sys.argv[1]; L=open(p).read().split('\n'); i=next(k for k,x in enumerate(L) if x.strip() and int(x,16)!=0)
L[i]=format(int(L[i],16)^0x80000000,'0%dx'%len(L[i].strip())); open(p,'w').write('\n'.join(L)); print('XCORRUPT line',i)
PY
  run1 XC_P$XC $XC $C
fi
gzip -f $O/run_*.log
echo WOB_SEQ_DONE $LEG $F
