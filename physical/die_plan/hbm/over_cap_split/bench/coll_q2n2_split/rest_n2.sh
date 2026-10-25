#!/bin/bash
# rest_n2.sh : body_n2 = ot_hfd_coll_q2_hard_v8g_s #(NLINK 2, TP 192, AR_ITER 1, ROWS 256, VM_RT 81) minus u_ring / u_reduce / u_vmasm / u_writer (PATH-HBM/NE2 10-25)
D=/srv/opentallas-scratch2/claude/path-hbm/ne2; WT=$D/src
FILES=$D/q3b.files PARAMS=NLINK=2,TP=192,AR_ITER=1,ROWS=256,VM_RT=81 DEFINES=OT_COLL_ISSUER256_NATIVE32 \
 bash $WT/physical/die_plan/hbm/cores/harden/rest_extract.sh $WT $D/rest coll_q2n2_body_rest ot_hfd_coll_q2_hard_v8g_s \
 ot_hgi_coll_ring_ag,ot_hgi_coll_reduce_static_pr,ot_hgi_coll_vmasm_sliced_v7,ot_hgi_coll_static_vmwrite_roots_v6_physical \
 "c:u_body.u_ring,c:u_body.u_reduce,c:u_body.u_vmasm,c:u_body.u_writer" 32
