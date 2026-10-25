#!/bin/bash
# asm.sh OUT.v : bench-only split assembly of ot_hfd_coll_q3_hard_v8x_s from the rest2 parent view (PATH-HBM/Q3 10-25)
# pieces: body_core (rest) + edge (3 link_e_pr + argmax_tp192_pr) + vm + coll_q2 ring_ag / reduce cores; mutants 1..5.
D=/srv/opentallas-scratch2/claude/path-hbm/q3split; WT=/srv/opentallas-scratch2/claude/wt/path-hbm-q3-1025
P=$WT/rtl/hbm_accel/cores_split; Q3=$P/ot_hfd_coll_q3_hard_v8x; Q2=$P/ot_hfd_coll_q2_hard_v8g
python3 -I $WT/physical/die_plan/hbm/cores/harden/split_asm.py --parent $D/rest2/coll_q3_body_rest2.parent.v --top q3_asm3 \
 --rest $Q3/ot_hfd_coll_q3_body_core.sv:coll_q3_body_rest2 \
 --piece "$Q3/ot_hfd_coll_q3_edge_core.sv:\\u_body.g_link[0].u_link=u_link0,\\u_body.g_link[1].u_link=u_link1,\\u_body.g_link[2].u_link=u_link2,\\u_body.g_q3.t192.u_arg=u_arg" \
 --piece "$Q3/ot_hfd_coll_q3_vm_core.sv:\\u_body.u_vmasm=u_vmasm,\\u_body.u_writer=u_writer" \
 --piece "$Q2/ot_hfd_coll_q2_reduce_core.sv:\\u_body.u_reduce=u_reduce" \
 --piece "$Q2/ot_hfd_coll_q2_ring_ag_core.sv:\\u_body.u_ring=u_ring" \
 --mut 1:ot_hfd_coll_q2_reduce_core:reduce_in_v:0 --mut 2:ot_hfd_coll_q3_edge_core:link0_wr_v:0 \
 --mut 3:ot_hfd_coll_q3_edge_core:arg_start:0 --mut 4:ot_hfd_coll_q3_body_core:u_body_g_qcap_2_u_cap_src_v:0 \
 --mut 5:ot_hfd_coll_q3_body_core:u_body_arg_fault:0 --out $1
