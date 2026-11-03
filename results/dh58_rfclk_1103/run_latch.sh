#!/bin/bash
# DH58-RFCLK: HEAD die gate (DIE-HEAD-52 run_gate.sh form, main 08542fa9d7d die_sta_related) + launch-side lockup latch estimate
# usage: run_latch.sh OUT PLAN
set -u; S=/srv/opentallas-scratch2/claude/die-head-47; R=/srv/opentallas-scratch2/claude/die-head-48; D=$R/sta; V=/srv/opentallas-scratch2/claude/dh58/rfclk/wt/results/die_head_1027/views
T=/srv/opentallas-scratch2/claude/dh58/rfclk/wt/tools/die_plan; H=/srv/opentallas-scratch2/claude/dh58/rfclk
O=$1; PL=$2; shift 2; rm -rf $O; mkdir -p $O; cp -r $R/pin52/o_l48x_wf/regchar $O/
python3 $H/latch_eval_head.py $T $R/clk_st51/proof_l48w_sth --plan $PL --out $O --corner TT --corner FF --cppr-lca --clock-cell inv --margin-policy nominal --nominal-arrival single --hold-buffers HB4 --core-latency-ff 342 --core-view ot_s81hd_elemA_cv=$V/ot_s81hd_elemA_cv --core-view ot_s81hd_elemB_cv=$V/ot_s81hd_elemB_cv --count-align $R/clk_st51/bind_l48w_dm700.json --count-align-key part --ca-ring $D/ca_ring_hd_tile.json --ca-write-fall --latch-ckq 73 --latch-ckq-min 15 --dump $O/latch.json "$@" > $O.log 2>&1; echo rc $? >> $O.log
