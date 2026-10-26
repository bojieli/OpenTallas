#!/bin/bash
# TOK-QK-QCE 10-26: recompose the QCL measured-age token with the die-scope ledger edges + lane ages REPLACED by the
# bind-re-derived lists (rederive_edges.py on bus_groups_{ref441,v7}.json.gz); control q_none = QCV7 / QCL 288025.
# Engine tree/src = the TOK-QK-QCV7 compose dir (git archive 94cd97b7a + overlay, see compose_edges.py); QCL S8 ages.
set -e
C=/srv/opentallas-scratch2/claude/tok-qk-qce/compose; cd $C; Q=/srv/opentallas-scratch2/claude/tok-qk-qcl/r1/die
VF="$(cat $Q/vflags.txt)"; A="$Q/build/slice_ages.json $Q/build/vec_ages.json $Q/cal_mat/stn_ages.json"
run() { python3 compose_edges.py $C "$@"; }
n=q_none;                 run $n $A "$VF" $C/edges_none.json &
for t in ref441 v7; do
  n=q_${t}_re;            run $n $A "$VF" --replace $C/edges_${t}_rederived.json $C/lane_ages_${t}_rederived.json &
  n=q_${t}_re_clamp;      run $n $A "$VF" --replace $C/edges_${t}_rederived_clamp.json $C/lane_ages_${t}_rederived_clamp.json &
  n=q_${t}_re_edgesonly;  run $n $A "$VF" --replace $C/edges_${t}_rederived.json - &
done
wait
