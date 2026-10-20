#!/bin/bash
# TOKSIM-S81C/FSEQ 10-19: the whole phase SEQUENCE of op(s) OPS on one slice-0 die frame, on the RELEASE frame exe of its die
# instance (build_seq.sh = release 19bf4121e die.v master + lk; bench tb_toksim_fgu_seq.sv = FGU 4cd48a7ab +RETIRE: a
# phase's rows are written back to the spine after its last calendar RET word, so op tags retire and >4-phase sequences
# run; + this lane's +PHASE_VM for the BF router, whose phases carry one K segment of x each).  Vectors = toksim_fsmall_gen.py
# per-phase vectors; seq dir + seqw.hex by toksim_fseq_seqops.py; every RET word assigned by calendar and checked per
# phase by toksim_fgu_check.py seq (xs_place check of record: golden segment-tree values bit-exact, row coverage, one tag,
# cycle-exact calendar, fixture BF16/fp32 tie where the fixture holds the op output).
# (XP=s: the 4cd48a7ab tb exes without +PHASE_VM; default v = this lane tb)
# usage: run_fseq.sh VECROOT LAYER FRAME NAME PHASE_VM "PERS" OP...     (cwd = $R/src2)
set -u
R=/srv/opentallas-scratch/claude/toksim-s81c-fseq; VR=$1; L=$2; F=$3; NM=$4; PV=$5; PERS=$6; shift 6
V=$VR/$L/$F; O=$R/run/$L/$F/$NM; mkdir -p $O; Q=tools/s81_dv/layer_prog/qf_producer
case $F in u_f_?L00|u_f_?R00) B=${XP:-v}_h9nx_e5;; u_f_?L01|u_f_?R01) B=${XP:-v}_h10_e2;; u_f_?L02|u_f_?R02) B=${XP:-v}_h9MX_e1;; u_f_?L03|u_f_?R03) B=${XP:-v}_h9nx_e2;; esac
X=$R/$B/obj/Vtb_toksim_fgu_seq; [ -x $X ] || { echo "NO_EXE $X"; exit 3; }
$X +verilator+version 2>/dev/null | head -1
FL=""; [ "$PV" = 1 ] && FL=--phase-vm
S=$(python3 $Q/toksim_fseq_seqops.py --vec $V --name $NM $FL --ops "$@"); echo "$S"
[ "${S%% *}" = SEQ ] || { echo FSEQ_NOSEQ $L $F $NM; exit 0; }
read _ SD NPH K OPS PH0 <<< "$S"
for P in $PERS; do
  T=$((NPH * P + 1200)); tg=P${P}
  timeout 1200 $X +OT_ROM_DIR=$SD +T=$T +K=$K +OPS=$OPS +PH=$PH0 +NPH=$NPH +PER=$P +RETIRE=1 +PHASE_VM=$PV > $O/run_seq_$tg.log 2>&1; rc=$?
  echo "FSEQ $L $F $NM $B rc=$rc $(python3 $Q/toksim_fgu_check.py seq --seq $SD --vec $V --log $O/run_seq_$tg.log --out $O/res_seq_$tg.json --per $P --ref-go 63 2>&1 | tail -1)"
done
gzip -f $O/run_*.log
echo FSEQ_FRAME_DONE $L $F $NM
