#!/bin/bash
# S81-RATE3: RTAG r2 wo_a sequences (vectors vecw/L0, the WQBP/FWOA wo_a phase set: frames 0L00/0L01 only)
set -u
R=/srv/opentallas-scratch/claude/s81-rtag-1020; cd $R/src
for F in u_f_0L00 u_f_0L01; do bash $R/rt_seq.sh $R/vecw/L0/$F $F woa attn.wo_a r160 "129,130,231" & done
bash $R/rt_seq.sh $R/vecw/L0/u_f_0L01 u_f_0L01 woa attn.wo_a rlate "130" &
wait; echo RT_R2B_DONE
