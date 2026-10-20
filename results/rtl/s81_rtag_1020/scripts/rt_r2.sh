#!/bin/bash
# S81-RATE3 10-20: S81-RTAG revision 2 (ot_s81_so_label_q 16-bit chunks / unreset copies, sha a43e28d3, unit census PASS max32)
# build 4 release frame classes SOQ=1 SWD=160 + MUT_LATE negative, then wo_a/router static go sequences at P129/130/231.
set -u
R=/srv/opentallas-scratch/claude/s81-rtag-1020; cd $R
[ -d src_r2 ] || { cp -al src src_r2 && rm src_r2/rtl/v41rom/ot_s81_so_label_q.sv && cp csrc/rtl/v41rom/ot_s81_so_label_q.sv src_r2/rtl/v41rom/; }
sha256sum src_r2/rtl/v41rom/ot_s81_so_label_q.sv
cd src_r2
b() { EXTRA_DEFS="-DDSFD_BF_SOQ=1 -DDSFD_BF_SOQ_SWD=160 $5" bash $R/build_seq.sh $1 $2 $3 $4; }
b col_h9_l4_nx 5 3 r160_h9nx_e5 "" > $R/b_r160_h9nx_e5.log 2>&1 &
b col_h10_l4 2 1 r160_h10_e2 "" > $R/b_r160_h10_e2.log 2>&1 &
b col_h9_MX_l4 1 0 r160_h9MX_e1 "" > $R/b_r160_h9MX_e1.log 2>&1 &
b col_h9_l4_nx 2 1 r160_h9nx_e2 "" > $R/b_r160_h9nx_e2.log 2>&1 &
b col_h10_l4 2 1 rlate_h10_e2 "-DOT_S81_SOQ_MUT_LATE" > $R/b_rlate_h10_e2.log 2>&1 &
wait
tail -n1 $R/b_r*.log
cd $R/src
for F in u_f_0L00 u_f_0L01 u_f_0L02 u_f_0L03; do
  bash $R/rt_seq.sh $R/vec/L0/$F $F woa attn.wo_a r160 "129,130,231" &
  bash $R/rt_seq.sh $R/vec/L0/$F $F router ffn.router r160 "129,130,231" &
done
bash $R/rt_seq.sh $R/vec/L0/u_f_0L01 u_f_0L01 woa attn.wo_a rlate "130" &
bash $R/rt_seq.sh $R/vec/L0/u_f_0L01 u_f_0L01 router ffn.router rlate "130" &
wait
echo RT_R2_DONE
