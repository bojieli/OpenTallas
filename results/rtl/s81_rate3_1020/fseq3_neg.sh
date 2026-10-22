#!/bin/bash
# S81-RATE3: extra negative periods for ffn.down (P-1 still passes: the compile floor 130 has margin); reuse the seq
set -u
D=/srv/opentallas-scratch/claude/s81-rate3; Q=/srv/opentallas-scratch/codex/s81-rom12-1020/fseq_src; cd $D/root
for FB in "u_f_0L00 v_h9nx_e5" "u_f_3L01 v_h10_e2"; do set -- $FB; V=$D/out/fseq3/$1/down; X=/srv/opentallas-scratch/claude/toksim-s81c-fseq/$2/obj/Vtb_toksim_fgu_seq
  read _ SD NPH K ROWS PH0 < $V/sequence_gen.log
  for P in 125 120; do
    timeout 1800 $X +OT_ROM_DIR=$SD +T=$((NPH*P+1500)) +K=$K +OPS=$ROWS +PH=$PH0 +NPH=$NPH +PER=$P +RETIRE=1 +PHASE_VM=1 > $V/run_P$P.log 2>&1
    echo "FSEQ3N $1 down P $P $(python3 $Q/toksim_fgu_check.py seq --seq $SD --vec $V --log $V/run_P$P.log --out $V/check_P$P.json --per $P --ref-go 63 2>&1 | tail -1)" &
  done
done; wait; echo FSEQ3N_DONE
