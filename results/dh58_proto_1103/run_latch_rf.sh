#!/bin/bash
# DH58-PROTO: DH58-RFCLK run_latch.sh form (DIE-HEAD-52 run_gate + launch lockup-latch model, die_sta_related on main) on the
# l48rf prototype die clock proof.  usage: run_latch_rf.sh OUT PROOF BIND [extra die_sta args]
set -u; R=/srv/opentallas-scratch2/claude/die-head-48; D=$R/sta; P=/srv/opentallas-scratch2/claude/dh58/proto; W=$P/wt
V=$W/results/die_head_1027/views; VP=$W/results/dh58_proto_1103/views; T=$W/tools/die_plan
PL=/srv/opentallas-scratch2/claude/dh58/rfplan_work/g5/source_plan.json
O=$1; PR=$2; B=$3; shift 3; rm -rf $O; mkdir -p $O; cp -r $R/pin52/o_l48x_wf/regchar $O/
python3 $W/results/dh58_rfclk_1103/latch_eval_head.py $T $PR --plan $PL --out $O --corner TT --corner FF --cppr-lca --clock-cell inv --margin-policy nominal --nominal-arrival single --hold-buffers HB4 --core-latency-ff 342 --core-view ot_s81hd_elemA_cv=$V/ot_s81hd_elemA_cv --core-view ot_s81hd_elemB_cv=$V/ot_s81hd_elemB_cv --core-view ot_s81hd_lep_pair=$VP/ot_s81hd_lep_pair --count-align $B --count-align-key part --ca-ring $D/ca_ring_hd_tile.json --ca-write-fall --latch-ckq 73 --latch-ckq-min 15 --dump $O/latch.json "$@" > $O.log 2>&1; echo rc $? >> $O.log
