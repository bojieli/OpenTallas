#!/bin/bash
# S81-ROMOPT-A: FSEQ benches; usage fseqa.sh CFG(o1o2|o1) FRAME BUILD OP:P[:NEG,NEG] ...
set -u; D=/srv/opentallas-scratch/claude/s81-romopt-a; cd $D/root; export PYTHONDONTWRITEBYTECODE=1
CFG=$1 FR=$2 BLD=$3; shift 3
case $CFG in o1) export OT_XS_QPAIRS=10 OT_XS_COMPACT_TAILS=0;; o1o2nc) export OT_XS_COMPACT_TAILS=0;; o1o2c) export OT_XS_COMPACT_TAILS=1;; esac
for spec in "$@"; do IFS=: read OP P NEG <<< "$spec"
  timeout 7200 python3 $D/fseqa.py $D/out/fseq_$CFG $FR $BLD $OP $P ${NEG//,/ } > $D/out/fseq_${CFG}_${FR}_${OP}.log 2>&1
  echo "FSEQA_JOB $CFG $FR $OP rc=$? $(grep -E 'FSEQA |FSEQA_VERDICT|Error' $D/out/fseq_${CFG}_${FR}_${OP}.log | cut -c1-220 | tr '\n' '|')"
done
