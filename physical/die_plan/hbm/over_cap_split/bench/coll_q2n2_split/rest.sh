#!/bin/bash
# rest.sh [WT] [OUT]: body remainder of ot_hfd_coll_q2_hard_v8g_s #(NLINK 2, TP 192, AR_ITER 1, ROWS 256, VM_RT 81) for the NE hub
# (HBM-CORES-RTL 10-26): master minus u_body.u_ring / u_reduce (coll_q2 ring_ag / reduce cores, reused) and
# u_body.u_vmasm / u_writer (ot_hfd_coll_q2n2_vm_core); then rest_wrap.py -> ot_hfd_coll_q2n2_body_core.sv.
WT=$(readlink -f ${1:-$(git -C $(dirname $0) rev-parse --show-toplevel)}); OUT=${2:-/srv/opentallas-scratch2/claude/hbm-cores-rtl-1026}
B=$WT/physical/die_plan/hbm/over_cap_split/bench/coll_q2n2_split; H=$WT/physical/die_plan/hbm/cores/harden
FILES=$B/q2n2.files PARAMS=NLINK=2,TP=192,AR_ITER=1,ROWS=256,VM_RT=81 DEFINES=OT_COLL_ISSUER256_NATIVE32 \
 bash $H/rest_extract.sh $WT $OUT/rest coll_q2n2_body_rest ot_hfd_coll_q2_hard_v8g_s \
 ot_hgi_coll_ring_ag,ot_hgi_coll_reduce_static_pr,ot_hgi_coll_vmasm_sliced_v7,ot_hgi_coll_static_vmwrite_roots_v6_physical \
 "c:u_body.u_ring,c:u_body.u_reduce,c:u_body.u_vmasm,c:u_body.u_writer" 48 || exit 2
# use_body.json: the 8 vm_rr valid bits (b*257+256) are the only vm_rr bits the remainder reads (data -> vm core vmasm_rd_il);
# clk_reduce[0] only (clk_reduce[32:1] = reduce core).  Checked against the extract: grep of vm_rr[N]/clk_reduce[N] references.
python3 -I $H/rest_wrap.py --ext $OUT/rest/coll_q2n2_body_rest.v --name coll_q2n2_body_rest --top ot_hfd_coll_q2n2_body_core \
 --use $B/use_body.json --parent $OUT/rest/coll_q2n2_body_rest.parent.v \
 --out $WT/rtl/hbm_accel/cores_split/ot_hfd_coll_q2n2_hard_v8g/ot_hfd_coll_q2n2_body_core.sv \
 --hdr "// GENERATED (HBM-CORES-RTL 2026-10-26) by physical/die_plan/hbm/over_cap_split/bench/coll_q2n2_split/rest.sh (rest_extract.sh + rest_wrap.py): ot_hfd_coll_q2_hard_v8g_s #(NLINK 2, TP 192, AR_ITER 1, ROWS 256, VM_RT 81) -DOT_COLL_ISSUER256_NATIVE32 minus u_body.u_ring / u_body.u_reduce / u_body.u_vmasm / u_body.u_writer; vm_rr data bits (vm core) and clk_reduce[32:1] (reduce core) dropped. Do not edit."
