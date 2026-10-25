#!/bin/bash
WT=/srv/opentallas-scratch2/claude/wt/path-hbm-q3-1025; D=/srv/opentallas-scratch2/claude/path-hbm/q3split
FILES=/srv/opentallas-scratch2/claude/path-hbm/q3synth/q3.files PARAMS=NLINK=3,TP=192,AR_ITER=1,ROWS=256,VM_RT=81 DEFINES=OT_COLL_ISSUER256_NATIVE32 \
 bash $WT/physical/die_plan/hbm/cores/harden/rest_extract.sh $WT $D/rest2 coll_q3_body_rest2 ot_hfd_coll_q3_hard_v8x_s \
 ot_hgi_coll_ring_ag,ot_hgi_coll_reduce_static_pr,ot_hgi_coll_link_e,ot_hgi_coll_argmax_m_tp192,ot_hgi_coll_vmasm_sliced_v7,ot_hgi_coll_static_vmwrite_roots_v6_physical \
 "c:u_body.u_ring,c:u_body.u_reduce,c:u_body.g_link*,c:*u_arg,c:u_body.u_vmasm,c:u_body.u_writer" 32
