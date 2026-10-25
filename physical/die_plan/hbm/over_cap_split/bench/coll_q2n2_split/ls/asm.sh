#!/bin/bash
# asm.sh OUT.v : bench-only split assembly of ot_hfd_coll_q2_hard_v8g_s #(NLINK 2) from the rest parent view (PATH-HBM/NE2 10-25)
# pieces: body_n2 (rest) + q2n2 vm_core (q3 vm_core members, tkw folded) + coll_q2 ring_ag / reduce cores; mutants 1..5.
D=/srv/opentallas-scratch2/claude/path-hbm/ne2; WT=$D/src; P=$WT/rtl/hbm_accel/cores_split; Q3=$P/ot_hfd_coll_q3_hard_v8x; Q2=$P/ot_hfd_coll_q2_hard_v8g
python3 -I $WT/physical/die_plan/hbm/cores/harden/split_asm.py --parent $D/rest/coll_q2n2_body_rest.parent.v --top q2n2_asm \
 --rest $P/ot_hfd_coll_q2n2_hard_v8g/ot_hfd_coll_q2n2_body_core.sv:coll_q2n2_body_rest \
 --piece "$P/ot_hfd_coll_q2n2_hard_v8g/ot_hfd_coll_q2n2_vm_core.sv:\\u_body.u_vmasm=u_vmasm,\\u_body.u_writer=u_writer" \
 --piece "$Q2/ot_hfd_coll_q2_reduce_core.sv:\\u_body.u_reduce=u_reduce" \
 --piece "$Q2/ot_hfd_coll_q2_ring_ag_core.sv:\\u_body.u_ring=u_ring" \
 --mut 1:ot_hfd_coll_q2_reduce_core:reduce_in_v:0 --mut 2:ot_hfd_coll_q2n2_vm_core:writer_rgx_v:0 \
 --mut 3:ot_hfd_coll_q2_ring_ag_core:ring_lp_we:0 --mut 4:ot_hfd_coll_q2n2_body_core:u_body_g_qcap_8_u_cap_src_v:0 \
 --mut 5:ot_hfd_coll_q2n2_vm_core:vmasm_sel:0 --out $1
