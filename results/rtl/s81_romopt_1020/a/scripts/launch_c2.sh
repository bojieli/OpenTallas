#!/bin/bash
cd /tmp
for FB in "u_f_0L00 v_h9nx_e5" "u_f_2L00 v_h9nx_e5" "u_f_3L01 v_h10_e2" "u_f_3L02 v_h9MX_e1"; do set -- $FB
  /home/ubuntu/bin/ot-run --mem 12 --threads 2 --dir /srv/opentallas-scratch/claude/s81-romopt-a -- bash /srv/opentallas-scratch/claude/s81-romopt-a/fseqa.sh o1o2c $1 $2 attn.wq_b:126 attn.wo_b:127 ffn.shared_gu:146 > /tmp/romopta/fseq_o1o2c2_$1.otrun.log 2>&1 &
done; wait; echo ALL_DONE_C2
