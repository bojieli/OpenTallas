#!/bin/bash
# ext.sh: rest of the body with u_qout cut, by the core's own rest_extract, on a small source tree.
set -u; Q=/srv/opentallas-scratch2/claude/hbm-reform-b5/q2n; R=/srv/opentallas-scratch3/claude/hbm-reform-b3/wt
rm -rf $Q/src2; cp -a $Q/src $Q/src2; P=rtl/hbm_accel/generic/collective/p2p; D=rtl/hbm_accel/cores_split/reform_1105b
cp $Q/gen/ot_q2nf_master.sv $Q/src2/$P/ot_hfd_coll_q2_hard_v8g_s.sv; mkdir -p $Q/src2/$D; cp $Q/gen/ot_q2nf_split.sv $Q/src2/$D/
{ cat $Q/q2n2.files; echo $D/ot_q2nf_split.sv; } > $Q/q2n2b.files
git -C $R show 97b0810d61:physical/die_plan/hbm/cores/harden/rest_extract.sh > $Q/rest_extract.sh
FILES=$Q/q2n2b.files PARAMS=NLINK=2,TP=192,AR_ITER=1,ROWS=256,VM_RT=81 DEFINES=OT_COLL_ISSUER256_NATIVE32 \
 bash $Q/rest_extract.sh $Q/src2 $Q/rest ot_q2nf_rest_x ot_hfd_coll_q2_hard_v8g_s \
 ot_hgi_coll_ring_ag,ot_hgi_coll_reduce_static_pr,ot_hgi_coll_vmasm_sliced_v7,ot_hgi_coll_static_vmwrite_roots_v6_physical,ot_q2nf_qout \
 "c:u_body.u_ring,c:u_body.u_reduce,c:u_body.u_vmasm,c:u_body.u_writer,c:u_body.u_qout" 48
tail -3 $Q/rest/ot_q2nf_rest_x.log | cut -c1-200; grep -i error $Q/rest/ot_q2nf_rest_x.log | head | cut -c1-240
cat $Q/rest/ot_q2nf_rest_x.excl | cut -c1-100
awk '{print $1,$2,$3}' $Q/rest/ot_q2nf_rest_x.ports | grep -i "qout\|q2f\|clk_qslots\|source_d" | cut -c1-110 | head -30
