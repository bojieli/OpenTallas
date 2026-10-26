#!/bin/bash
# TOK-QK-PRICE 10-26: compose every case of cases.json with ../compose_edges.py (QCE engine tree, QCL S8 ages; ~8 s,
# 180 MB each). Ran on intel2 (light python): C = own compose root with tree/src symlinked to the TOK-QK-QCE compose dir.
set -e
B=/srv/opentallas-scratch2/claude/tok-qk-price-0130; C=$B/compose; IN=$B/in    # IN = copy of ./out
Q=/srv/opentallas-scratch2/claude/tok-qk-qcl/r1/die; VF="$(cat $Q/vflags.txt)"
A="$Q/build/slice_ages.json $Q/build/vec_ages.json $Q/cal_mat/stn_ages.json"
cd $C
for n in v7ctl v7ctl_ext v7fe v7fe_lawhop v7cl_aln v7fecl_aln v7cl_lit v7fecl_lit; do
  nice python3 compose_edges.py $C q_$n $A "$VF" --replace $IN/edges_${n}_rederived.json $IN/lane_ages_${n}_rederived.json &
done
wait
