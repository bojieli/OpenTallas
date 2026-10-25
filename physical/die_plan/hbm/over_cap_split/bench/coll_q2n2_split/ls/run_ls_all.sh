#!/bin/bash
# run_ls_all.sh : verilate + per-unit compile + lock-step runs of the q2n2 split assembly (PATH-HBM/NE2 10-25)
cd /srv/opentallas-scratch2/claude/path-hbm/ne2/ls
FILES=/srv/opentallas-scratch2/claude/path-hbm/ne2/q3b.files ./build.sh n2 q2n2_asm tb.sv asm.v /srv/opentallas-scratch2/claude/path-hbm/ne2/src/rtl/hbm_accel/cores_split/ot_hfd_coll_q2n2_hard_v8g/ot_hfd_coll_q2n2_body_core.sv /srv/opentallas-scratch2/claude/path-hbm/ne2/src/rtl/hbm_accel/cores_split/ot_hfd_coll_q2n2_hard_v8g/ot_hfd_coll_q2n2_vm_core.sv /srv/opentallas-scratch2/claude/path-hbm/ne2/src/rtl/hbm_accel/cores_split/ot_hfd_coll_q2_hard_v8g/ot_hfd_coll_q2_ring_ag_core.sv /srv/opentallas-scratch2/claude/path-hbm/ne2/src/rtl/hbm_accel/cores_split/ot_hfd_coll_q2_hard_v8g/ot_hfd_coll_q2_reduce_core.sv || exit 2
./comp_ind.sh n2 32 || exit 3
./run_ls.sh n2 2000
